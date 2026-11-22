# -*- coding: utf-8 -*-
"""Prueba de rendimiento y estrés del prototipo AZA Analyzer.

Mide latencia por endpoint, comportamiento bajo concurrencia, escrituras
simultáneas y el costo del análisis de visión. Guarda resultados en JSON y
deja un registro de consola para la evidencia.

Uso:  python pruebas_carga/estres.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import psutil

BASE = os.getenv("AZA_BASE", "http://127.0.0.1:8000")
SALIDA = os.path.dirname(os.path.abspath(__file__))
LOG = []
RES = {"base": BASE, "inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "escenarios": {}}


def log(texto=""):
    print(texto)
    LOG.append(texto)


def pct(datos, q):
    if not datos:
        return 0.0
    datos = sorted(datos)
    k = (len(datos) - 1) * q
    bajo, alto = int(k), min(int(k) + 1, len(datos) - 1)
    return datos[bajo] + (datos[alto] - datos[bajo]) * (k - bajo)


def resumen(latencias, errores, segundos):
    return {
        "peticiones": len(latencias),
        "errores": errores,
        "tasa_error_pct": round(100 * errores / max(1, len(latencias)), 2),
        "rps": round(len(latencias) / segundos, 2) if segundos else 0,
        "media_ms": round(statistics.mean(latencias), 2) if latencias else 0,
        "p50_ms": round(pct(latencias, 0.50), 2),
        "p95_ms": round(pct(latencias, 0.95), 2),
        "p99_ms": round(pct(latencias, 0.99), 2),
        "max_ms": round(max(latencias), 2) if latencias else 0,
    }


class Cliente:
    def __init__(self, usuario, pin):
        self.http = httpx.Client(base_url=BASE, timeout=120.0)
        r = self.http.post("/api/auth/login", json={"username": usuario, "pin": pin})
        r.raise_for_status()
        self.cab = {"Authorization": "Bearer " + r.json()["access"]}

    def medir(self, metodo, ruta, **kw):
        t0 = time.perf_counter()
        try:
            r = self.http.request(metodo, ruta, headers=self.cab, **kw)
            ok = 200 <= r.status_code < 300
            cuerpo = r.json() if ok and "application/json" in r.headers.get("content-type", "") else None
        except Exception as exc:                       # noqa: BLE001
            return (time.perf_counter() - t0) * 1000, False, {"error": str(exc)[:80]}
        return (time.perf_counter() - t0) * 1000, ok, cuerpo


def medir_servidor(pid):
    try:
        p = psutil.Process(pid)
        p.cpu_percent(None)
        return p
    except Exception:
        return None


def muestrear(proceso, muestras, stop_flag):
    """Muestrea CPU y memoria del servidor mientras corre la prueba."""
    while not stop_flag["fin"]:
        try:
            cpu = proceso.cpu_percent(None) if proceso else 0
            ram = proceso.memory_info().rss / 1024 / 1024 if proceso else 0
            muestras.append({"t": time.time(), "cpu": cpu, "ram_mb": round(ram, 1)})
        except Exception:
            pass
        time.sleep(0.5)


def escenario_latencia(cli):
    log("")
    log("== ESCENARIO 1 · Latencia por endpoint (secuencial, 60 repeticiones) ==")
    rutas = [
        ("GET", "/api/health", "Salud"),
        ("GET", "/api/dashboard", "Dashboard"),
        ("GET", "/api/inspecciones?tamano=20", "Histórico (20 filas)"),
        ("GET", "/api/inspecciones/5", "Detalle de inspección"),
    ]
    salida = {}
    for metodo, ruta, nombre in rutas:
        lat, err = [], 0
        for _ in range(60):
            ms, ok, _c = cli.medir(metodo, ruta)
            lat.append(ms)
            err += 0 if ok else 1
        r = resumen(lat, err, sum(lat) / 1000)
        salida[nombre] = r
        log(f"  {nombre:<26} media {r['media_ms']:7.1f} ms · p95 {r['p95_ms']:7.1f} ms · "
            f"p99 {r['p99_ms']:7.1f} ms · errores {r['errores']}")
    return salida


def escenario_concurrencia(cli, niveles=(1, 5, 10, 20), segundos=12):
    log("")
    log(f"== ESCENARIO 2 · Lecturas concurrentes ({segundos} s por nivel) ==")
    rutas = ["/api/dashboard", "/api/inspecciones?tamano=20", "/api/inspecciones/5"]
    salida = []
    for nivel in niveles:
        lat, err = [], 0
        fin = time.time() + segundos

        def worker(_i):
            nonlocal err
            while time.time() < fin:
                for ruta in rutas:
                    if time.time() >= fin:
                        break
                    ms, ok, _c = cli.medir("GET", ruta)
                    lat.append(ms)
                    if not ok:
                        err += 1

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=nivel) as pool:
            list(pool.map(worker, range(nivel)))
        total = time.time() - t0
        r = resumen(lat, err, total)
        r["nivel"] = nivel
        salida.append(r)
        log(f"  {nivel:>2} clientes  {r['rps']:7.1f} req/s · media {r['media_ms']:7.1f} ms · "
            f"p95 {r['p95_ms']:7.1f} ms · p99 {r['p99_ms']:7.1f} ms · errores {r['errores']}")
    return salida


def escenario_escrituras(cli_escritura, niveles=(1, 5, 10), por_nivel=40):
    log("")
    log("== ESCENARIO 3 · Escrituras concurrentes (registro por API) ==")
    salida, creadas = [], []
    for nivel in niveles:
        lat, err, ids = [], 0, []

        def worker(_i):
            nonlocal err
            for _ in range(por_nivel // nivel):
                ms, ok, cuerpo = cli_escritura.medir(
                    "POST", "/api/inspecciones",
                    json={"id_receta": 1, "angulo": 70.0, "id_lote": 1, "id_batch": 1})
                lat.append(ms)
                if ok and cuerpo:
                    ids.append(cuerpo.get("id"))
                else:
                    err += 1

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=nivel) as pool:
            list(pool.map(worker, range(nivel)))
        total = time.time() - t0
        r = resumen(lat, err, total)
        r["nivel"] = nivel
        r["creadas"] = len([i for i in ids if i])
        salida.append(r)
        creadas.extend([i for i in ids if i])
        log(f"  {nivel:>2} clientes  {r['creadas']:>3} registros · {r['rps']:6.1f} reg/s · "
            f"media {r['media_ms']:7.1f} ms · p95 {r['p95_ms']:7.1f} ms · errores {r['errores']}")
    return salida, creadas


def escenario_vision(cli):
    log("")
    log("== ESCENARIO 4 · Análisis de visión (ráfaga completa, 3 veces) ==")
    lat, err, detalles = [], 0, []
    for _ in range(3):
        ms, ok, cuerpo = cli.medir("POST", "/api/simular?receta_id=1&velocidad=12&modo=dentro")
        lat.append(ms)
        if ok and cuerpo:
            detalles.append({"duracion_ms": cuerpo.get("duracion_ms"),
                             "angulo": cuerpo.get("medicion", {}).get("angulo"),
                             "frames": cuerpo.get("rafaga", {}).get("frames")})
        else:
            err += 1
        log(f"  ráfaga {len(lat)}: {ms:7.0f} ms · ángulo {detalles[-1]['angulo'] if detalles else '-'}")
    r = resumen(lat, err, sum(lat) / 1000)
    r["detalles"] = detalles
    return r


def main():
    log("=" * 68)
    log(" PRUEBA DE RENDIMIENTO Y ESTRÉS · AZA Analyzer")
    log("=" * 68)
    log(f" Servidor   : {BASE}")
    log(f" Equipo     : Windows {sys.getwindowsversion().major}.{sys.getwindowsversion().minor} · "
        f"{os.cpu_count()} núcleos · {round(psutil.virtual_memory().total / 1024**3, 1)} GB RAM")
    log(f" Inicio     : {RES['inicio']}")

    cli = Cliente("jsarabia", "1234")
    cli_w = Cliente("servicio", "servicio")
    salud = cli.http.get("/api/health").json()
    log(f" Backend    : {salud['base']} · {salud['almacen']}")
    log(f" Registros  : {salud['inspecciones']}")
    RES["backend"] = salud["base"]
    RES["registros_iniciales"] = salud["inspecciones"]

    proceso = None
    pid_dado = os.getenv("AZA_PID")
    if pid_dado and pid_dado.isdigit():
        try:
            proceso = psutil.Process(int(pid_dado))
        except Exception:
            proceso = None
    if proceso is None:
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                linea = " ".join(p.info["cmdline"] or [])
                if "uvicorn" in linea and "app.main" in linea:
                    proceso = psutil.Process(p.info["pid"])
                    break
            except Exception:
                continue
    RES["proceso"] = proceso.pid if proceso else None
    log(f" Servidor   : PID {RES['proceso']}" if proceso else " Servidor   : PID no detectado")

    muestras, stop = [], {"fin": False}
    import threading
    hilo = threading.Thread(target=muestrear, args=(proceso, muestras, stop), daemon=True)
    hilo.start()

    RES["escenarios"]["latencia"] = escenario_latencia(cli)
    RES["escenarios"]["concurrencia"] = escenario_concurrencia(cli)
    escrituras, creadas = escenario_escrituras(cli_w)
    RES["escenarios"]["escrituras"] = escrituras
    RES["ids_creados"] = creadas
    RES["escenarios"]["vision"] = escenario_vision(cli)

    stop["fin"] = True
    time.sleep(0.8)
    if muestras:
        RES["recursos"] = {
            "cpu_medio_pct": round(statistics.mean(m["cpu"] for m in muestras), 1),
            "cpu_max_pct": round(max(m["cpu"] for m in muestras), 1),
            "ram_media_mb": round(statistics.mean(m["ram_mb"] for m in muestras), 1),
            "ram_max_mb": round(max(m["ram_mb"] for m in muestras), 1),
            "muestras": muestras,
        }
        log("")
        log(f"== Recursos del servidor durante la prueba ==")
        log(f"  CPU media {RES['recursos']['cpu_medio_pct']}% · pico {RES['recursos']['cpu_max_pct']}% · "
            f"RAM media {RES['recursos']['ram_media_mb']} MB")

    RES["fin"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(SALIDA, "resultados.json"), "w", encoding="utf-8") as fh:
        json.dump(RES, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(SALIDA, "consola.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG))
    log("")
    log("=" * 68)
    log(" Prueba terminada · resultados.json y consola.log guardados")
    log("=" * 68)


if __name__ == "__main__":
    main()
