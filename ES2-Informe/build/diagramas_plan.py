"""Diagramas de planificación: Gantt, red de dependencias, estados y priorización."""
import datetime as dt
import sys
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dib import (PALETA, guardar, lienzo, caja, caja_izq, flecha, titulo,
                 banda, contenedor, leyenda, nota, linea, elipse)

D = dt.date

# (id, actividad, inicio, fin, responsable, sprint)
ACTIVIDADES = [
    ("A01", "Conformación del equipo y acta de constitución",  D(2026, 8, 10), D(2026, 8, 12), "LD", 0),
    ("A02", "Definición de metodología (Scrum + RUP 4+1)",      D(2026, 8, 11), D(2026, 8, 13), "JS", 0),
    ("A03", "Levantamiento de actores y necesidades",           D(2026, 8, 12), D(2026, 8, 19), "LD", 0),
    ("A04", "Historias de usuario y criterios de aceptación",   D(2026, 8, 24), D(2026, 9, 2),  "LD", 1),
    ("A05", "Catálogo RF/RNF y matriz de trazabilidad",         D(2026, 8, 31), D(2026, 9, 4),  "DP", 1),
    ("A06", "Backlog priorizado con MoSCoW",                    D(2026, 8, 24), D(2026, 8, 27), "LD", 1),
    ("A07", "Selección y justificación del stack tecnológico",  D(2026, 8, 25), D(2026, 8, 31), "JS", 1),
    ("A08", "Arquitectura general y vistas 4+1",                D(2026, 8, 26), D(2026, 9, 8),  "JS", 1),
    ("A09", "Prototipo navegable v1 (wireframes)",              D(2026, 8, 27), D(2026, 9, 10), "DP", 1),
    ("A10", "Validación con usuarios y registro de feedback",   D(2026, 9, 7),  D(2026, 9, 11), "LD", 1),
    ("A11", "Modelo de datos y DER",                            D(2026, 9, 14), D(2026, 9, 24), "JS", 2),
    ("A12", "Diccionario de datos y DDL de PostgreSQL",         D(2026, 9, 21), D(2026, 9, 28), "JS", 2),
    ("A13", "Políticas de autenticación y autorización",        D(2026, 9, 15), D(2026, 9, 25), "JS", 2),
    ("A14", "Análisis de amenazas y mitigaciones",              D(2026, 9, 18), D(2026, 9, 29), "JS", 2),
    ("A15", "Estándares de codificación segura",                D(2026, 9, 22), D(2026, 9, 30), "DP", 2),
    ("A16", "Prototipo v2 con feedback aplicado",               D(2026, 9, 21), D(2026, 10, 2), "DP", 2),
    ("A17", "Guía visual y adaptabilidad responsive",           D(2026, 9, 24), D(2026, 10, 2), "DP", 2),
    ("A18", "Plan de pruebas (unitarias, integrales, rendimiento)", D(2026, 10, 5), D(2026, 10, 12), "DP", 3),
    ("A19", "Herramientas manuales y automatizadas",            D(2026, 10, 7),  D(2026, 10, 13), "DP", 3),
    ("A20", "Umbrales de rendimiento y ensayo de consultas",    D(2026, 10, 9),  D(2026, 10, 15), "JS", 3),
    ("A21", "Redacción del informe ES2 y anexos",               D(2026, 10, 8),  D(2026, 10, 16), "LD", 3),
    ("A22", "Revisión interna y entrega ES2",                   D(2026, 10, 15), D(2026, 10, 16), "LD", 3),
    ("A23", "Implementación de backend y API REST",             D(2026, 10, 20), D(2026, 11, 5),  "JS", 4),
    ("A24", "Implementación de frontend React",                 D(2026, 10, 20), D(2026, 11, 6),  "DP", 4),
    ("A25", "Dashboard, consultas e indicadores",               D(2026, 11, 9),  D(2026, 11, 17), "DP", 5),
    ("A26", "Despliegue cloud y pipeline CI/CD",                D(2026, 11, 9),  D(2026, 11, 18), "JS", 5),
    ("A27", "Pruebas de integración, rendimiento y UAT",        D(2026, 11, 16), D(2026, 11, 20), "LD", 5),
    ("A28", "Documentación final y manual de operación",        D(2026, 11, 23), D(2026, 12, 4),  "LD", 6),
    ("A29", "Ensayo de demostración y defensa",                 D(2026, 12, 7),  D(2026, 12, 11), "LD", 6),
]


SPRINTS = [
    (0, "Sprint 0\nInicio",        D(2026, 8, 10),  D(2026, 8, 21),  PALETA["morado"],  PALETA["morado_p"]),
    (1, "Sprint 1\nDiagnóstico",   D(2026, 8, 24),  D(2026, 9, 11),  PALETA["azul"],    PALETA["azul_p"]),
    (2, "Sprint 2\nDatos y seg.",  D(2026, 9, 14),  D(2026, 10, 2),  PALETA["verde"],   PALETA["verde_p"]),
    (3, "Sprint 3\nPruebas/ES2",   D(2026, 10, 5),  D(2026, 10, 16), PALETA["naranja"], PALETA["naranja_p"]),
    (4, "Sprint 4\nConstrucción",  D(2026, 10, 20), D(2026, 11, 6),  PALETA["rojo"],    PALETA["rojo_p"]),
    (5, "Sprint 5\nCloud y QA",    D(2026, 11, 9),  D(2026, 11, 20), PALETA["azul_o"],  "#E1F0FA"),
    (6, "Sprint 6\nCierre ES4",    D(2026, 11, 23), D(2026, 12, 11), PALETA["gris"],    PALETA["gris_p"]),
]


HITOS = [
    ("Entrega ES1 · 07-sep", D(2026, 9, 7), 0),
    ("Entrega ES2 · 19-oct", D(2026, 10, 19), 0),
    ("Entrega ES3 · 23-nov", D(2026, 11, 23), 0),
    ("Defensa ES4 · 14-dic", D(2026, 12, 14), 0),
]


RESP_NOMBRE = {"LD": "Leonardo Daza", "JS": "José Sarabia", "DP": "Daniel Paredes"}


def diagrama_gantt():
    n = len(ACTIVIDADES)
    fig, ax = plt.subplots(figsize=(15.5, 12.4))
    fig.patch.set_facecolor("white")

    y = np.arange(n)
    for i, (aid, nombre, ini, fin, resp, sp) in enumerate(ACTIVIDADES):
        fuerte = next(s[4] for s in SPRINTS if s[0] == sp)
        claro = next(s[5] for s in SPRINTS if s[0] == sp)
        x0 = mdates.date2num(ini)
        x1 = mdates.date2num(fin) + 1
        ax.barh(i, x1 - x0, left=x0, height=0.62, color=fuerte,
                edgecolor=claro, linewidth=1.0, alpha=0.92, zorder=3)
        ax.text(x1 + 1.4, i, resp, va="center", ha="left", fontsize=8.0,
                color=fuerte, weight="bold", zorder=6)

    # bandas de sprint
    for num, etiqueta, ini, fin, color, claro in SPRINTS:
        x0 = mdates.date2num(ini) - 1
        x1 = mdates.date2num(fin) + 2
        ax.axvspan(x0, x1, color=claro, alpha=0.55, zorder=0)
        ax.axvline(x0, color=color, lw=0.9, ls=(0, (4, 3)), zorder=1)
        ax.text((x0 + x1) / 2, -2.4, etiqueta, ha="center", va="center",
                fontsize=8.4, color=color, weight="bold", linespacing=1.25, zorder=6)

    # hitos
    for etiqueta, fecha, fila in HITOS:
        x = mdates.date2num(fecha) + 1
        ax.axvline(x, color=PALETA["rojo"], lw=1.1, ls=(0, (2, 2)), alpha=0.75, zorder=2)
        ax.plot([x], [n + 0.9], marker="D", markersize=11, color=PALETA["rojo"],
                markeredgecolor="white", markeredgewidth=1.2, zorder=7)
        ax.text(x, n + 1.9, etiqueta, fontsize=8.4, weight="bold",
                color=PALETA["rojo"], ha="center", va="center", zorder=7)

    ax.set_yticks(y)
    etiquetas = [f"{a[0]}  {a[1][:58]}" for a in ACTIVIDADES]
    ax.set_yticklabels(etiquetas, fontsize=8.2, color=PALETA["texto"])
    ax.set_ylim(n + 2.9, -4.0)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
    for lbl in ax.get_xticklabels():
        lbl.set_fontsize(8.0)
        lbl.set_color(PALETA["gris"])
    ax.grid(axis="x", which="major", color=PALETA["gris_m"], alpha=0.35, lw=0.7, zorder=0)
    ax.set_xlim(mdates.date2num(D(2026, 8, 8)), mdates.date2num(D(2026, 12, 26)))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(PALETA["gris_m"])
    ax.spines["bottom"].set_color(PALETA["gris_m"])

    ax.set_title("Cronograma del proyecto — Scrum con 7 sprints (agosto a diciembre 2026)",
                 fontsize=14, weight="bold", color=PALETA["gris"], pad=16, loc="left")

    fig.text(0.012, 0.012,
             "Responsables:  LD = Leonardo Daza (Product Owner)   ·   "
             "JS = José Sarabia (Scrum Master / Backend)   ·   "
             "DP = Daniel Paredes (Frontend / QA)",
             fontsize=8.4, color=PALETA["gris"], style="italic")

    fig.tight_layout(rect=(0, 0.022, 1, 1))
    return guardar(fig, "01_cronograma_gantt.png")


def diagrama_red_dependencias():
    import textwrap as tw
    fig, ax = lienzo(15.4, 8.6, 100, 100)
    titulo(ax, "Red de dependencias del cronograma y ruta crítica", y=99,
           sub="Cada actividad depende de la anterior (fin→inicio). En rojo, la ruta crítica: holgura cero.")

    nodos = [
        ("N1",  "Inicio y metodología", 0),
        ("N2",  "Necesidades, HU y RF", 0),
        ("N3",  "Backlog y stack", 0),
        ("N4",  "Arquitectura 4+1", 0),
        ("N5",  "Prototipo v1", 0),
        ("N6",  "Validación usuarios", 2),
        ("N7",  "Modelo de datos", 0),
        ("N8",  "Seguridad", 3),
        ("N9",  "Prototipo v2", 4),
        ("N10", "Plan de pruebas", 0),
        ("N11", "Informe ES2", 0),
        ("N12", "Backend + frontend", 0),
        ("N13", "Dashboard", 0),
        ("N14", "Despliegue cloud", 0),
        ("N15", "Integración y UAT", 0),
        ("N16", "Cierre y defensa", 0),
    ]

    xs = [2.0, 14.4, 26.8, 39.2, 51.6, 64.0, 76.4, 88.8]
    w, h = 10.8, 11.5
    fila1_y, fila2_y = 74.0, 40.0

    pos = {}
    for i, (aid, label, holg) in enumerate(nodos[:8]):
        pos[aid] = (xs[i], fila1_y)
    for i, (aid, label, holg) in enumerate(nodos[8:]):
        pos[aid] = (xs[7 - i], fila2_y)

    for aid, label, holg in nodos:
        x, y = pos[aid]
        critico = holg == 0
        fc = PALETA["rojo_p"] if critico else PALETA["azul_p"]
        ec = PALETA["rojo"] if critico else PALETA["azul"]
        txt = aid + "\n" + tw.fill(label, 15)
        if holg:
            txt += f"\n(+{holg} d)"
        caja(ax, x, y, w, h, txt, color=fc, borde=ec, fs=7.1, bold=False,
             wrap=None, radio=0.9, lw=1.8 if critico else 1.2)

    # flechas horizontales fila 1
    for i in range(7):
        a, b = nodos[i], nodos[i + 1]
        x1 = pos[a[0]][0] + w
        x2 = pos[b[0]][0]
        y = fila1_y + h / 2
        flecha(ax, (x1, y), (x2, y), color=PALETA["rojo"], lw=2.0, size=12)
        ax.text((x1 + x2) / 2, y + 1.4, "FS", ha="center", va="bottom",
                fontsize=6.4, color=PALETA["rojo"])

    # conector vertical N8 -> N9
    x_c = xs[7] + w / 2
    flecha(ax, (x_c, fila1_y), (x_c, fila2_y + h), color=PALETA["rojo"], lw=2.0, size=12)
    ax.text(x_c + 1.4, (fila1_y + fila2_y + h) / 2, "FS", ha="left", va="center",
            fontsize=6.4, color=PALETA["rojo"])

    # flechas horizontales fila 2 (derecha -> izquierda)
    for i in range(8, 15):
        a, b = nodos[i], nodos[i + 1]
        x1 = pos[a[0]][0]
        x2 = pos[b[0]][0] + w
        y = fila2_y + h / 2
        flecha(ax, (x1, y), (x2, y), color=PALETA["rojo"], lw=2.0, size=12)
        ax.text((x1 + x2) / 2, y + 1.4, "FS", ha="center", va="bottom",
                fontsize=6.4, color=PALETA["rojo"])

    # hitos
    hitos = [("N2", "Entrega ES1 · 07-sep"), ("N11", "Entrega ES2 · 19-oct"),
             ("N15", "Entrega ES3 · 23-nov"), ("N16", "Defensa ES4 · 14-dic")]
    for aid, texto in hitos:
        x, y = pos[aid]
        ax.plot([x + w / 2], [y + h + 2.6], marker="D", markersize=8,
                color=PALETA["amarillo"], markeredgecolor=PALETA["gris"],
                markeredgewidth=0.8, zorder=8)
        ax.text(x + w / 2, y + h + 4.4, texto, ha="center", va="bottom",
                fontsize=6.8, weight="bold", color=PALETA["gris"], zorder=8)

    # leyenda y nota
    leyenda(ax, [
        (PALETA["rojo_p"], PALETA["rojo"], "Ruta crítica — sin holgura: cualquier atraso mueve la entrega"),
        (PALETA["azul_p"], PALETA["azul"], "Actividad con holgura (puede atrasarse los días indicados)"),
    ], x=2, y=27, dy=3.6, ancho=60, fs=7.8)

    ax.text(2, 19.5, "Prioridad de ejecución: P1 = N1–N7 y N11 (bloquean el diseño) · "
                     "P2 = N8–N10 (paralelizables) · P3 = N12–N16 (construcción y cierre)",
            fontsize=7.6, color=PALETA["gris"], style="italic")

    nota(ax, 2, 14, "El informe ES2 (N11) solo puede cerrarse cuando N1–N10 están resueltos: "
                    "las vistas 4+1 dependen del modelo de datos y el plan de pruebas depende de "
                    "los prototipos. Las actividades N8 y N9 son paralelizables porque no bloquean "
                    "la entrega de ES2.", w=88)
    return guardar(fig, "02_red_dependencias.png")


def diagrama_estados():
    fig, ax = lienzo(15.6, 8.0, 100, 62)
    ax.set_ylim(6, 62)
    ax.text(50, 60.5, "Máquina de estados del objeto «Inspección»", ha="center",
            va="top", fontsize=15, color=PALETA["gris"], weight="bold")
    ax.text(50, 56.6, "Ciclo de vida del resultado: desde que ingresa por API hasta que se archiva",
            ha="center", va="top", fontsize=9, color=PALETA["gris_m"], style="italic")

    def c(x, y, w, h, txt, fc, ec, fs=9.4):
        caja(ax, x, y, w, h, txt, color=fc, borde=ec, bold=True, fs=fs, wrap=None, radio=0.8, lw=1.5)

    c(9, 30, 15, 9, "RECIBIDA", PALETA["gris_p"], PALETA["gris"])
    c(31, 30, 15, 9, "VALIDADA", PALETA["azul_p"], PALETA["azul"])
    c(53, 30, 16, 9, "EVALUADA", PALETA["amarillo_p"], PALETA["amarillo"])
    c(79, 39, 18, 8, "APROBADA", PALETA["verde_p"], PALETA["verde"])
    c(79, 28, 18, 8, "RECHAZADA", PALETA["rojo_p"], PALETA["rojo"])
    c(79, 17, 18, 8, "SIN RECETA", PALETA["naranja_p"], PALETA["naranja"])
    c(53, 12, 16, 8, "ARCHIVADA", PALETA["gris_p"], PALETA["gris_m"])

    ax.add_patch(plt.Circle((4.2, 34.5), 1.1, fc=PALETA["texto"], ec=PALETA["texto"], zorder=6))
    flecha(ax, (5.3, 34.5), (9, 34.5), color=PALETA["texto"], lw=1.6)

    # transiciones etiquetadas T1..T8
    flecha(ax, (24, 34.5), (31, 34.5), color=PALETA["gris"], lw=1.5)
    ax.text(27.5, 35.8, "T1", ha="center", va="bottom", fontsize=7.6, weight="bold",
            color=PALETA["gris"])
    flecha(ax, (46, 34.5), (53, 34.5), color=PALETA["gris"], lw=1.5)
    ax.text(49.5, 35.8, "T2", ha="center", va="bottom", fontsize=7.6, weight="bold",
            color=PALETA["gris"])

    flecha(ax, (69, 36), (79, 41.5), color=PALETA["verde"], lw=1.5, rad=-0.15)
    ax.text(72.5, 40.2, "T3", ha="center", va="center", fontsize=7.6, weight="bold",
            color=PALETA["verde"])
    flecha(ax, (69, 34.5), (79, 32), color=PALETA["rojo"], lw=1.5)
    ax.text(74, 34.0, "T4", ha="center", va="bottom", fontsize=7.6, weight="bold",
            color=PALETA["rojo"])
    flecha(ax, (69, 33), (79, 21), color=PALETA["naranja"], lw=1.5, rad=0.15)
    ax.text(72.2, 25.4, "T5", ha="center", va="center", fontsize=7.6, weight="bold",
            color=PALETA["naranja"])

    flecha(ax, (61, 30), (61, 20), color=PALETA["gris_m"], lw=1.5)
    ax.text(62.0, 25, "T6", ha="left", va="center", fontsize=7.6, weight="bold",
            color=PALETA["gris_m"])
    for x0, y0 in [(88, 39), (88, 28), (88, 17)]:
        flecha(ax, (x0, y0), (69, 15.5), color=PALETA["gris_m"], lw=1.2, rad=0.18)
    ax.text(78, 10.6, "T7 / T8 / T9 · archivar por retención o baja lógica",
            ha="center", va="top", fontsize=7.4, color=PALETA["gris_m"], style="italic")

    ax.text(4.2, 44.5, "[sin permisos o\nestado inválido]\n→ HTTP 403 / 409",
            ha="left", va="top", fontsize=7.2, color=PALETA["rojo"], linespacing=1.35)

    nota(ax, 2, 25.4, "T3–T5 se resuelven con los límites de la receta vigente al momento del "
                      "registro; el estado no se recalcula si la receta cambia después. "
                      "ARCHIVADA es de solo lectura.", w=46, ancho=32, fs=7.0)
    return guardar(fig, "03_estados_inspeccion.png")


def diagrama_priorizacion():
    fig, ax = lienzo(13.6, 9.2, 100, 100)
    titulo(ax, "Priorización del backlog: valor para el negocio vs. esfuerzo", y=99.5,
           sub="Ubicación de cada historia de usuario en la matriz de decisión (MoSCoW)")

    ox, oy, w, h = 15, 26, 68, 66
    ax.add_patch(Rectangle((ox, oy), w, h, fc="white", ec=PALETA["gris_m"], lw=1.2, zorder=1))
    ax.plot([ox + w / 2, ox + w / 2], [oy, oy + h], color=PALETA["gris_m"], lw=1.0, zorder=2)
    ax.plot([ox, ox + w], [oy + h / 2, oy + h / 2], color=PALETA["gris_m"], lw=1.0, zorder=2)

    for x, y, cw, ch, col in [
        (ox, oy + h / 2, w / 2, h / 2, PALETA["verde_p"]),
        (ox + w / 2, oy + h / 2, w / 2, h / 2, PALETA["azul_p"]),
        (ox, oy, w / 2, h / 2, PALETA["amarillo_p"]),
        (ox + w / 2, oy, w / 2, h / 2, PALETA["rojo_p"]),
    ]:
        ax.add_patch(Rectangle((x, y), cw, ch, fc=col, ec="none", alpha=0.55, zorder=1))

    # (esfuerzo %, valor %, etiqueta de dos líneas)
    puntos = [
        (12, 88, "HU-01\nAutenticarse"),
        (40, 88, "HU-02\nRegistrar inspección"),
        (12, 74, "HU-03\nConsultar histórico"),
        (40, 74, "HU-05\nAprobar / rechazar"),
        (12, 60, "HU-04\nFiltrar por lote"),
        (62, 88, "HU-06\nDashboard operador"),
        (88, 88, "HU-07\nTendencias supervisor"),
        (62, 74, "HU-08\nAlertas sin receta"),
        (88, 74, "HU-09\nAuditoría de cambios"),
        (62, 60, "HU-10\nGestión de recetas"),
        (12, 38, "HU-11\nExportar CSV"),
        (40, 38, "HU-12\nTema claro / oscuro"),
        (62, 38, "HU-13\nNotificación por correo"),
        (88, 38, "HU-14\nApp móvil nativa"),
        (62, 18, "HU-15\nIntegración ERP"),
        (88, 18, "HU-16\nTrazabilidad por imagen"),
    ]
    for ex, vy, txt in puntos:
        x = ox + w * ex / 100
        y = oy + h * vy / 100
        ax.scatter([x], [y], s=165, color=PALETA["verde"], edgecolor="white",
                   linewidth=1.4, zorder=6, alpha=0.95)
        ax.text(x, y - 3.0, txt, ha="center", va="top", fontsize=6.9,
                color=PALETA["texto"], zorder=7, linespacing=1.15)

    ax.annotate("", xy=(ox + w + 1.5, oy - 6.0), xytext=(ox - 1.5, oy - 6.0),
                arrowprops=dict(arrowstyle="-|>", color=PALETA["gris"], lw=1.4))
    ax.text(ox + w / 2, oy - 8.4, "Esfuerzo / complejidad de implementación  →",
            ha="center", va="top", fontsize=9, color=PALETA["gris"], weight="bold")
    ax.annotate("", xy=(ox - 5.5, oy + h + 1.5), xytext=(ox - 5.5, oy - 1.5),
                arrowprops=dict(arrowstyle="-|>", color=PALETA["gris"], lw=1.4))
    ax.text(ox - 9.0, oy + h / 2, "Valor para el negocio  →", ha="center", va="center",
            fontsize=9, color=PALETA["gris"], weight="bold", rotation=90)

    # leyenda MoSCoW
    leyenda(ax, [
        (PALETA["verde_p"], PALETA["verde"], "MUST HAVE — hacer primero"),
        (PALETA["amarillo_p"], PALETA["amarillo"], "COULD HAVE — rápido y opcional"),
    ], x=15, y=12.5, dy=5.0, fs=7.4)
    leyenda(ax, [
        (PALETA["azul_p"], PALETA["azul"], "SHOULD HAVE — planificar"),
        (PALETA["rojo_p"], PALETA["rojo"], "WON'T HAVE — no ahora"),
    ], x=54, y=12.5, dy=5.0, fs=7.4)
    return guardar(fig, "04_priorizacion_moscow.png")


if __name__ == "__main__":
    print("Generando diagramas de planificación...")
    diagrama_gantt()
    diagrama_red_dependencias()
    diagrama_estados()
    diagrama_priorizacion()
    print("Listo.")
