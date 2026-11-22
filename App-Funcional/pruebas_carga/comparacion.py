# -*- coding: utf-8 -*-
"""Compara la prueba local (SQLite) con la prueba en la nube (PostgreSQL + S3)."""
import html
import json
import os
import subprocess
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(os.path.dirname(BASE), "evidencias")
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

LOCAL = json.load(open(os.path.join(BASE, "resultados.json"), encoding="utf-8"))
NUBE = json.load(open(os.path.join(BASE, "resultados_nube.json"), encoding="utf-8"))

VERDE = "#154A1C"
VERDE_CLARO = "#9CC4A6"
AMBAR = "#B7791F"
GRIS = "#607D8B"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": "#C9D4CE", "axes.titleweight": "bold", "axes.titlecolor": VERDE,
    "figure.facecolor": "white", "axes.grid": True, "grid.color": "#E3E8EA",
    "grid.linewidth": 0.8, "axes.axisbelow": True, "axes.titlesize": 11,
})


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(os.path.join(EVID, nombre), dpi=140, facecolor="white")
    plt.close(fig)
    print("   ok  ", nombre)


# ---------------------------------------- 1. escrituras: SQLite vs PostgreSQL
el = LOCAL["escenarios"]["escrituras"]
en = NUBE["escenarios"]["escrituras"]
niveles = sorted({e["nivel"] for e in el} | {e["nivel"] for e in en})
mapa_l = {e["nivel"]: e for e in el}
mapa_n = {e["nivel"]: e for e in en}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.0))
x = range(len(niveles))
ancho = 0.36
ax1.bar([i - ancho / 2 for i in x], [mapa_l[n]["rps"] for n in niveles], ancho,
        label="SQLite (demo local)", color=VERDE_CLARO)
ax1.bar([i + ancho / 2 for i in x], [mapa_n[n]["rps"] for n in niveles], ancho,
        label="PostgreSQL (AWS)", color=VERDE)
ax1.set_xticks(list(x))
ax1.set_xticklabels([f"{n} cliente{'s' if n > 1 else ''}" for n in niveles])
ax1.set_ylabel("registros por segundo")
ax1.set_title("Escrituras por segundo")
ax1.legend(frameon=False, fontsize=8.5, loc="upper left")
for i, n in enumerate(niveles):
    ax1.text(i - ancho / 2, mapa_l[n]["rps"] + 1.2, f"{mapa_l[n]['rps']:.1f}", ha="center", fontsize=8.5)
    ax1.text(i + ancho / 2, mapa_n[n]["rps"] + 1.2, f"{mapa_n[n]['rps']:.1f}", ha="center",
             fontsize=8.5, color=VERDE)

ax2.bar([i - ancho / 2 for i in x], [mapa_l[n]["p95_ms"] for n in niveles], ancho,
        label="SQLite (demo local)", color=VERDE_CLARO)
ax2.bar([i + ancho / 2 for i in x], [mapa_n[n]["p95_ms"] for n in niveles], ancho,
        label="PostgreSQL (AWS)", color=VERDE)
ax2.set_xticks(list(x))
ax2.set_xticklabels([f"{n} cliente{'s' if n > 1 else ''}" for n in niveles])
ax2.set_ylabel("latencia p95 (ms)")
ax2.set_title("Latencia de escritura (p95)")
ax2.legend(frameon=False, fontsize=8.5, loc="upper left")
for i, n in enumerate(niveles):
    ax2.text(i - ancho / 2, mapa_l[n]["p95_ms"] + 70, f"{mapa_l[n]['p95_ms']:.0f}", ha="center", fontsize=8.5)
    ax2.text(i + ancho / 2, mapa_n[n]["p95_ms"] + 70, f"{mapa_n[n]['p95_ms']:.0f}", ha="center",
             fontsize=8.5, color=VERDE)
ax2.set_ylim(0, max(mapa_l[n]["p95_ms"] for n in niveles) * 1.18)
fig.suptitle("Escrituras concurrentes · SQLite vs PostgreSQL", fontsize=12,
             fontweight="bold", color=VERDE, y=1.0)
fig.subplots_adjust(top=0.84)
guardar(fig, "37_estres_comparacion_escrituras.png")

# ------------------------------------------------ 2. latencia: local vs nube
ll = LOCAL["escenarios"]["latencia"]
ln = NUBE["escenarios"]["latencia"]
nombres = list(ll.keys())
fig, ax = plt.subplots(figsize=(8.8, 4.0))
x = range(len(nombres))
ax.bar([i - ancho / 2 for i in x], [ll[n]["p95_ms"] for n in nombres], ancho,
       label="Local (SQLite, 127.0.0.1)", color=VERDE_CLARO)
ax.bar([i + ancho / 2 for i in x], [ln[n]["p95_ms"] for n in nombres], ancho,
       label="Nube (PostgreSQL + S3, us-east-1)", color=VERDE)
ax.set_xticks(list(x))
ax.set_xticklabels(nombres, fontsize=8.5)
ax.set_ylabel("latencia p95 (ms)")
ax.set_title("Latencia por endpoint · el peso de la red")
ax.legend(frameon=False, fontsize=8.5)
for i, n in enumerate(nombres):
    ax.text(i - ancho / 2, ll[n]["p95_ms"] + 4, f"{ll[n]['p95_ms']:.0f}", ha="center", fontsize=8.5)
    ax.text(i + ancho / 2, ln[n]["p95_ms"] + 4, f"{ln[n]['p95_ms']:.0f}", ha="center", fontsize=8.5, color=VERDE)
ax.set_ylim(0, max(ln[n]["p95_ms"] for n in nombres) * 1.2)
guardar(fig, "38_estres_comparacion_latencia.png")

# ------------------------------------------------------- 3. tabla comparativa
ESTILO = """
 body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef1f2;margin:0;padding:26px;color:#1c2427}
 h1{font-size:19px;margin:0 0 4px;color:#154a1c}
 .sub{color:#607d8b;font-size:12.5px;margin-bottom:16px}
 .card{background:#f7f9f9;border:1px solid #d6ddde;border-radius:10px;padding:16px 18px;margin-bottom:16px}
 h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#154a1c;margin:0 0 10px}
 table{width:100%;border-collapse:collapse;font-size:12px}
 th{background:#154a1c;color:#fff;padding:7px 9px;text-align:left;font-size:10.5px;text-transform:uppercase}
 td{padding:6px 9px;border-bottom:1px solid #e3e8ea;font-family:Consolas,monospace}
 tr:nth-child(even) td{background:#eef3ef}
 .mejor{color:#154a1c;font-weight:700}
"""


def fila(etiqueta, a, b, mejor):
    clase_a = " class='mejor'" if mejor == "a" else ""
    clase_b = " class='mejor'" if mejor == "b" else ""
    return f"<tr><td>{etiqueta}</td><td{clase_a}>{a}</td><td{clase_b}>{b}</td></tr>"


filas = [
    fila("Latencia p95 de lectura (dashboard)", f"{ll['Dashboard']['p95_ms']} ms", f"{ln['Dashboard']['p95_ms']} ms", "a"),
    fila("Escrituras con 1 cliente", f"{mapa_l[1]['rps']} reg/s", f"{mapa_n[1]['rps']} reg/s", "a"),
    fila("Escrituras con 10 clientes", f"{mapa_l[10]['rps']} reg/s", f"{mapa_n[10]['rps']} reg/s", "b"),
    fila("Latencia p95 de escritura (10 clientes)", f"{mapa_l[10]['p95_ms']} ms", f"{mapa_n[10]['p95_ms']} ms", "b"),
    fila("Lecturas con 20 clientes", f"{LOCAL['escenarios']['concurrencia'][-1]['rps']} req/s",
         f"{NUBE['escenarios']['concurrencia'][-1]['rps']} req/s", "b"),
    fila("Tiempo de una ráfaga de visión", f"{LOCAL['escenarios']['vision']['media_ms']} ms",
         f"{NUBE['escenarios']['vision']['media_ms']} ms", "a"),
    fila("Errores en toda la prueba", "0 %", "0 %", None),
]

pagina = f"""<!doctype html><html><head><meta charset='utf-8'><style>{ESTILO}</style></head><body>
<h1>Comparación · demo local vs despliegue en la nube</h1>
<div class='sub'>Misma aplicación, mismo código, mismo generador de carga. Cambia el motor de base de datos
y la ubicación: SQLite en el equipo vs PostgreSQL 16 + S3 en AWS (us-east-1).</div>
<div class='card'><h2>Resultados</h2><table>
<tr><th>Métrica</th><th>SQLite local</th><th>PostgreSQL en AWS</th></tr>
{''.join(filas)}
</table></div>
<div class='card'><h2>Lectura de los resultados</h2>
<table>
<tr><th>Observación</th><th>Por qué</th></tr>
<tr><td>La nube suma ~140 ms a cada petición</td><td>Distancia Chile → us-east-1 (ida y vuelta). No es la base: hasta /api/health tarda lo mismo.</td></tr>
<tr><td>SQLite no escala en escrituras (8 reg/s planos)</td><td>Un solo candado de archivo serializa todas las escrituras, sin importar los núcleos.</td></tr>
<tr><td>PostgreSQL sí escala (8 → 51 reg/s)</td><td>Concurrencia real: varias transacciones en paralelo.</td></tr>
<tr><td>p95 de escritura: 3.480 ms vs 307 ms</td><td>La cola de espera de SQLite crece; PostgreSQL la mantiene acotada.</td></tr>
<tr><td>La visión tarda lo mismo en ambos</td><td>Es CPU pura: 2,3–3,1 s por ráfaga de 16 imágenes.</td></tr>
</table></div>
</body></html>"""

ruta = os.path.join(tempfile.gettempdir(), "ev_comparacion.html")
with open(ruta, "w", encoding="utf-8") as fh:
    fh.write(pagina)
perfil = tempfile.mkdtemp(prefix="aza_comp_")
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--window-size=1440,1200", "--virtual-time-budget=3000",
                f"--user-data-dir={perfil}",
                f"--screenshot={os.path.join(EVID, '39_estres_comparacion.png')}",
                "file:///" + ruta.replace("\\", "/")],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
print("   ok   39_estres_comparacion.png")
