# -*- coding: utf-8 -*-
"""Genera los gráficos y las capturas de la prueba de estrés."""
import base64
import html
import json
import os
import subprocess
import tempfile
import time
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(BASE)
EVID = os.path.join(APP, "evidencias")
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
RES = json.load(open(os.path.join(BASE, "resultados.json"), encoding="utf-8"))

VERDE = "#154A1C"
VERDE_CLARO = "#7BAE86"
AMBAR = "#B7791F"
ROJO = "#9B2C2C"
GRIS = "#607D8B"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": "#C9D4CE", "axes.labelcolor": "#1C2427",
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": VERDE,
    "figure.facecolor": "white", "axes.grid": True, "grid.color": "#E3E8EA",
    "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def guardar(fig, nombre):
    ruta = os.path.join(EVID, nombre)
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, facecolor="white")
    plt.close(fig)
    print("   ok  ", nombre)


# ------------------------------------------------------ 1. latencia por ruta
lat = RES["escenarios"]["latencia"]
nombres = list(lat.keys())
fig, ax = plt.subplots(figsize=(8.6, 4.2))
x = range(len(nombres))
ancho = 0.26
ax.bar([i - ancho for i in x], [lat[n]["media_ms"] for n in nombres], ancho, label="Media", color=VERDE_CLARO)
ax.bar(list(x), [lat[n]["p95_ms"] for n in nombres], ancho, label="p95", color=VERDE)
ax.bar([i + ancho for i in x], [lat[n]["p99_ms"] for n in nombres], ancho, label="p99", color=AMBAR)
ax.set_xticks(list(x))
ax.set_xticklabels(nombres, fontsize=8.5)
ax.set_ylabel("milisegundos")
ax.set_title("Latencia por endpoint · 60 peticiones secuenciales")
ax.legend(frameon=False, ncol=3, loc="upper left")
for i, n in enumerate(nombres):
    ax.text(i, lat[n]["p99_ms"] + 1.5, f"{lat[n]['p99_ms']:.0f}", ha="center", fontsize=8, color=AMBAR)
guardar(fig, "30_estres_latencia.png")

# ------------------------------------------------- 2. lecturas concurrentes
con = RES["escenarios"]["concurrencia"]
niveles = [c["nivel"] for c in con]
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ax.plot(niveles, [c["rps"] for c in con], "o-", color=VERDE, linewidth=2.2, label="Throughput (req/s)")
ax.set_xlabel("clientes concurrentes")
ax.set_ylabel("req/s", color=VERDE)
ax.set_xticks(niveles)
ax2 = ax.twinx()
ax2.plot(niveles, [c["p95_ms"] for c in con], "s--", color=AMBAR, linewidth=2, label="Latencia p95 (ms)")
ax2.set_ylabel("p95 (ms)", color=AMBAR)
ax2.grid(False)
for i, c in enumerate(con):
    ax.text(c["nivel"], c["rps"] + 3, f"{c['rps']:.0f}", ha="center", color=VERDE, fontsize=8.5)
    ax2.text(c["nivel"], c["p95_ms"] + 18, f"{c['p95_ms']:.0f} ms", ha="center", color=AMBAR, fontsize=8.5)
ax.set_title("Lecturas concurrentes · 12 s por nivel")
ax.set_ylim(0, max(c["rps"] for c in con) * 1.35)
ax2.set_ylim(0, max(c["p95_ms"] for c in con) * 1.35)
guardar(fig, "31_estres_concurrencia.png")

# ------------------------------------------------- 3. escrituras concurrentes
esc = RES["escenarios"]["escrituras"]
niveles_e = [e["nivel"] for e in esc]
fig, ax = plt.subplots(figsize=(8.6, 4.2))
barras = ax.bar([str(n) for n in niveles_e], [e["p95_ms"] for e in esc], color=[VERDE_CLARO, VERDE, AMBAR])
ax.set_xlabel("clientes concurrentes")
ax.set_ylabel("latencia p95 (ms)")
ax.set_title("Escrituras concurrentes · 40 registros por nivel")
for b, e in zip(barras, esc):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 60,
            f"{e['p95_ms']:.0f} ms\n{e['rps']:.1f} reg/s", ha="center", fontsize=9)
ax.set_ylim(0, max(e["p95_ms"] for e in esc) * 1.3)
guardar(fig, "32_estres_escrituras.png")

# --------------------------------------------------------- 4. CPU y memoria
rec = RES.get("recursos", {})
muestras = rec.get("muestras", [])
if muestras:
    t0 = muestras[0]["t"]
    xs = [m["t"] - t0 for m in muestras]
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    ax.plot(xs, [m["cpu"] for m in muestras], color=VERDE, linewidth=1.6, label="CPU (%)")
    ax.axhline(100, color=GRIS, linestyle=":", linewidth=1)
    ax.text(1, 104, "1 núcleo = 100 %", fontsize=8, color=GRIS)
    ax.set_xlabel("segundos desde el inicio")
    ax.set_ylabel("CPU del servidor (%)", color=VERDE)
    ax.set_title("Consumo de recursos durante la prueba")
    ax2 = ax.twinx()
    ax2.plot(xs, [m["ram_mb"] for m in muestras], color=AMBAR, linewidth=1.4, label="RAM (MB)")
    ax2.set_ylabel("RAM (MB)", color=AMBAR)
    ax2.grid(False)
    ax2.yaxis.set_major_locator(MaxNLocator(5))
    guardar(fig, "33_estres_recursos.png")

# --------------------------------------------------- evidencia: consola real
ESTILO = """
 body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef1f2;margin:0;padding:26px;color:#1c2427}
 h1{font-size:19px;margin:0 0 4px;color:#154a1c}
 .sub{color:#607d8b;font-size:12.5px;margin-bottom:16px}
 pre{background:#0f1a12;color:#c8e6c9;padding:16px 18px;border-radius:10px;font-size:11.5px;line-height:1.5;
     font-family:'Cascadia Mono',Consolas,monospace;white-space:pre-wrap;margin:0}
 table{width:100%;border-collapse:collapse;font-size:12px;background:#f7f9f9}
 th{background:#154a1c;color:#fff;padding:7px 9px;text-align:left;font-size:10.5px;text-transform:uppercase}
 td{padding:6px 9px;border-bottom:1px solid #e3e8ea;font-family:Consolas,monospace}
 tr:nth-child(even) td{background:#eef3ef}
 .card{background:#f7f9f9;border:1px solid #d6ddde;border-radius:10px;padding:16px 18px;margin-bottom:16px}
 h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#154a1c;margin:0 0 10px}
"""


def capturar_html(cuerpo, destino, alto=1250):
    pagina = (f"<!doctype html><html><head><meta charset='utf-8'><style>{ESTILO}</style></head>"
              f"<body>{cuerpo}</body></html>")
    ruta = os.path.join(tempfile.gettempdir(), "ev_estres.html")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(pagina)
    perfil = tempfile.mkdtemp(prefix="aza_estres_")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size=1440,{alto}", "--virtual-time-budget=3000",
                    f"--user-data-dir={perfil}", f"--screenshot={destino}",
                    "file:///" + ruta.replace("\\", "/")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


log_txt = open(os.path.join(BASE, "consola.log"), encoding="utf-8").read()
capturar_html(
    "<h1>Salida de la prueba de rendimiento y estrés</h1>"
    f"<div class='sub'>Ejecución real contra el servidor local · {html.escape(RES['base'])} · "
    f"{html.escape(RES['inicio'])}</div><pre>{html.escape(log_txt)}</pre>",
    os.path.join(EVID, "34_estres_consola.png"), 1150)
print("   ok   34_estres_consola.png")

filas = []
for nombre, r in RES["escenarios"]["latencia"].items():
    filas.append(f"<tr><td>{html.escape(nombre)}</td><td>{r['peticiones']}</td><td>{r['media_ms']}</td>"
                 f"<td>{r['p95_ms']}</td><td>{r['p99_ms']}</td><td>{r['max_ms']}</td><td>{r['errores']}</td></tr>")
tabla_lat = ("<div class='card'><h2>Escenario 1 · latencia secuencial</h2><table>"
             "<tr><th>Endpoint</th><th>Peticiones</th><th>Media ms</th><th>p95</th><th>p99</th>"
             "<th>Máx</th><th>Errores</th></tr>" + "".join(filas) + "</table></div>")

filas = []
for c in RES["escenarios"]["concurrencia"]:
    filas.append(f"<tr><td>{c['nivel']}</td><td>{c['peticiones']}</td><td>{c['rps']}</td><td>{c['media_ms']}</td>"
                 f"<td>{c['p95_ms']}</td><td>{c['p99_ms']}</td><td>{c['tasa_error_pct']}%</td></tr>")
tabla_con = ("<div class='card'><h2>Escenario 2 · lecturas concurrentes (12 s por nivel)</h2><table>"
             "<tr><th>Clientes</th><th>Peticiones</th><th>req/s</th><th>Media ms</th><th>p95</th>"
             "<th>p99</th><th>Errores</th></tr>" + "".join(filas) + "</table></div>")

filas = []
for e in RES["escenarios"]["escrituras"]:
    filas.append(f"<tr><td>{e['nivel']}</td><td>{e['creadas']}</td><td>{e['rps']}</td><td>{e['media_ms']}</td>"
                 f"<td>{e['p95_ms']}</td><td>{e['tasa_error_pct']}%</td></tr>")
v = RES["escenarios"]["vision"]
tabla_esc = ("<div class='card'><h2>Escenario 3 · escrituras concurrentes</h2><table>"
             "<tr><th>Clientes</th><th>Registros</th><th>reg/s</th><th>Media ms</th><th>p95</th>"
             "<th>Errores</th></tr>" + "".join(filas) + "</table></div>"
             f"<div class='card'><h2>Escenario 4 · análisis de visión</h2><table>"
             "<tr><th>Ráfaga</th><th>Duración ms</th><th>Ángulo</th><th>Frames</th></tr>"
             + "".join(f"<tr><td>{i+1}</td><td>{d['duracion_ms']}</td><td>{d['angulo']}°</td>"
                       f"<td>{d['frames']}</td></tr>"
                       for i, d in enumerate(v.get("detalles", [])))
             + f"<tr><td colspan='2'>Media</td><td colspan='2'>{v['media_ms']} ms</td></tr></table></div>")

rec_txt = ""
if rec:
    rec_txt = (f"<div class='card'><h2>Recursos del servidor</h2><table>"
               f"<tr><th>Métrica</th><th>Valor</th></tr>"
               f"<tr><td>CPU media</td><td>{rec['cpu_medio_pct']} %</td></tr>"
               f"<tr><td>CPU máxima</td><td>{rec['cpu_max_pct']} %</td></tr>"
               f"<tr><td>RAM media</td><td>{rec['ram_media_mb']} MB</td></tr>"
               f"<tr><td>RAM máxima</td><td>{rec['ram_max_mb']} MB</td></tr></table></div>")

capturar_html(
    "<h1>Resultados de la prueba</h1>"
    f"<div class='sub'>{html.escape(RES['backend'])} · {RES['registros_iniciales']} registros iniciales · "
    f"{html.escape(RES['inicio'])} a {html.escape(RES['fin'])}</div>"
    + tabla_lat + tabla_con + tabla_esc + rec_txt,
    os.path.join(EVID, "35_estres_resultados.png"), 1500)
print("   ok   35_estres_resultados.png")
print("gráficos y evidencias listos")
