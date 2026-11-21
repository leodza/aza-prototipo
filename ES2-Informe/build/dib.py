"""Utilidades de dibujo compartidas para los diagramas del informe ES2."""
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse, Rectangle, Circle

DIR_DIAG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "diagramas"))
os.makedirs(DIR_DIAG, exist_ok=True)

PALETA = {
    "verde":     "#2E7D32",
    "verde_o":   "#1B5E20",
    "verde_c":   "#4CAF50",
    "verde_p":   "#E8F5E9",
    "azul":      "#1565C0",
    "azul_o":    "#0D47A1",
    "azul_p":    "#E3F2FD",
    "gris":      "#37474F",
    "gris_m":    "#78909C",
    "gris_p":    "#ECEFF1",
    "naranja":   "#E65100",
    "naranja_p": "#FFF3E0",
    "rojo":      "#C62828",
    "rojo_p":    "#FFEBEE",
    "morado":    "#4527A0",
    "morado_p":  "#EDE7F6",
    "amarillo":  "#F9A825",
    "amarillo_p":"#FFFDE7",
    "blanco":    "#FFFFFF",
    "texto":     "#212121",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "savefig.facecolor": "white",
})


def lienzo(ancho, alto, xmax=100.0, ymax=100.0):
    """Crea una figura con sistema de coordenadas 0..xmax / 0..ymax y sin ejes."""
    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def titulo(ax, texto, x=None, y=98.5, fs=15, color=None, sub=None):
    """Título del diagrama (y subtítulo opcional)."""
    color = color or PALETA["gris"]
    x = 50.0 if x is None else x
    ax.text(x, y, texto, ha="center", va="top", fontsize=fs, color=color,
            weight="bold", zorder=5)
    if sub:
        ax.text(x, y - 4.2, sub, ha="center", va="top", fontsize=9,
                color=PALETA["gris_m"], style="italic", zorder=5)


def caja(ax, x, y, w, h, texto, color=None, borde=None, tc=None, fs=9,
         bold=False, wrap=24, radio=0.7, lw=1.3, style="normal"):
    """Caja redondeada con texto centrado."""
    color = color or PALETA["gris_p"]
    borde = borde or color
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radio}",
                       fc=color, ec=borde, lw=lw, zorder=2)
    ax.add_patch(p)
    t = textwrap.fill(texto, wrap) if wrap else texto
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs,
            color=tc or PALETA["texto"],
            weight="bold" if bold else "normal", zorder=3,
            linespacing=1.35, style=style)
    return p


def _linea_unidades(ax, fs, lsp=1.35):
    """Altura de una línea de texto (en unidades del lienzo) para un tamaño de fuente dado."""
    y0, y1 = ax.get_ylim()
    fig_h = ax.figure.get_size_inches()[1]
    escala = abs(y1 - y0) / fig_h if fig_h else 1.0
    return fs * lsp / 72.0 * escala


def caja_izq(ax, x, y, w, h, titulo_txt, sub, color=None, borde=None, tc=None,
             fs=9, fs_sub=7.6, wrap_t=26, wrap_s=34, radio=0.7, lw=1.3):
    """Caja con un título en negrita arriba y un subtítulo pequeño debajo."""
    color = color or PALETA["gris_p"]
    borde = borde or color
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radio}",
                       fc=color, ec=borde, lw=lw, zorder=2)
    ax.add_patch(p)
    cx = x + w / 2
    tt = textwrap.fill(titulo_txt, wrap_t) if wrap_t else titulo_txt
    st = textwrap.fill(sub, wrap_s) if wrap_s else sub
    n_t = tt.count("\n") + 1
    n_s = st.count("\n") + 1
    lh_t = _linea_unidades(ax, fs)
    lh_s = _linea_unidades(ax, fs_sub)
    total = n_t * lh_t + n_s * lh_s + lh_s * 0.5
    top = y + h / 2 + total / 2
    ax.text(cx, top, tt, ha="center", va="top", fontsize=fs,
            color=tc or PALETA["texto"], weight="bold", zorder=3,
            linespacing=1.3)
    ax.text(cx, top - n_t * lh_t - lh_s * 0.45, st, ha="center", va="top",
            fontsize=fs_sub, color=tc or PALETA["gris"], zorder=3, linespacing=1.3)
    return p


def elipse(ax, cx, cy, w, h, texto, color=None, borde=None, fs=8.6, wrap=20):
    """Elipse (para casos de uso)."""
    color = color or PALETA["azul_p"]
    borde = borde or PALETA["azul"]
    e = Ellipse((cx, cy), w, h, fc=color, ec=borde, lw=1.3, zorder=2)
    ax.add_patch(e)
    t = textwrap.fill(texto, wrap) if wrap else texto
    ax.text(cx, cy, t, ha="center", va="center",
            fontsize=fs, zorder=3, linespacing=1.3)
    return e


def actor(ax, cx, cy, nombre, color=None, escala=1.0, fs=8.6):
    """Figura de actor UML (palito)."""
    color = color or PALETA["gris"]
    r = 1.9 * escala
    ax.add_patch(Circle((cx, cy + 4.6 * escala), r, fc="white", ec=color, lw=1.6, zorder=3))
    ax.plot([cx, cx], [cy + 4.6 * escala - r, cy - 1.6 * escala], color=color, lw=1.6, zorder=3)
    ax.plot([cx - 2.6 * escala, cx + 2.6 * escala], [cy + 1.2 * escala, cy + 1.2 * escala],
            color=color, lw=1.6, zorder=3)
    ax.plot([cx, cx - 2.2 * escala], [cy - 1.6 * escala, cy - 4.6 * escala], color=color, lw=1.6, zorder=3)
    ax.plot([cx, cx + 2.2 * escala], [cy - 1.6 * escala, cy - 4.6 * escala], color=color, lw=1.6, zorder=3)
    ax.text(cx, cy - 7.0 * escala, textwrap.fill(nombre, 16), ha="center", va="top",
            fontsize=fs, color=PALETA["texto"], weight="bold", zorder=3)


def flecha(ax, xy1, xy2, color=None, rad=0.0, lw=1.5, ls="-", etiqueta=None,
           fs=7.4, estilo="-|>", size=11, tc=None, ha="center", va="center",
           dx=0.0, dy=0.0, zorder=4):
    """Flecha entre dos puntos con curvatura opcional y etiqueta."""
    color = color or PALETA["gris"]
    a = FancyArrowPatch(xy1, xy2, connectionstyle=f"arc3,rad={rad}",
                        arrowstyle=estilo, mutation_scale=size,
                        color=color, lw=lw, linestyle=ls, zorder=zorder,
                        shrinkA=1, shrinkB=1)
    ax.add_patch(a)
    if etiqueta:
        mx = (xy1[0] + xy2[0]) / 2 + dx
        my = (xy1[1] + xy2[1]) / 2 + dy
        ax.text(mx, my, textwrap.fill(etiqueta, 18), ha=ha, va=va, fontsize=fs,
                color=tc or color, zorder=zorder + 1,
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.92))
    return a


def linea(ax, xy1, xy2, color=None, lw=1.3, ls="-", zorder=3):
    color = color or PALETA["gris"]
    ax.plot([xy1[0], xy2[0]], [xy1[1], xy2[1]], color=color, lw=lw, ls=ls, zorder=zorder)


def banda(ax, x, y, w, h, texto, color=None, tc=None, fs=8.4, rot=0, bold=True):
    """Banda/etiqueta de agrupación."""
    color = color or PALETA["gris_p"]
    ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="none", zorder=1, alpha=0.75))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs,
            color=tc or PALETA["gris"], weight="bold" if bold else "normal",
            rotation=rot, zorder=5)


def contenedor(ax, x, y, w, h, etiqueta, color=None, borde=None, fs=8.4, lw=1.2, ls="-"):
    """Contenedor punteado con etiqueta en la esquina (para diagramas de despliegue)."""
    color = color or PALETA["gris_m"]
    borde = borde or color
    ax.add_patch(Rectangle((x, y), w, h, fc="none", ec=borde, lw=lw, ls=ls, zorder=1))
    ax.text(x + 1.6, y + h - 1.8, etiqueta, ha="left", va="top", fontsize=fs,
            color=color, weight="bold", zorder=5)


def nota(ax, x, y, texto, fs=7.6, w=42, ancho=46.0, color=None, color_borde=None):
    """Nota al pie / aclaración estilo UML. `y` es el borde superior."""
    color = color or PALETA["amarillo_p"]
    color_borde = color_borde or PALETA["amarillo"]
    t = textwrap.fill(texto, w)
    n = t.count("\n") + 1
    lh = _linea_unidades(ax, fs)
    h = n * lh + lh * 1.3
    ax.add_patch(FancyBboxPatch((x, y - h), ancho, h,
                                boxstyle="round,pad=0,rounding_size=0.4",
                                fc=color, ec=color_borde, lw=1.0, zorder=5))
    ax.text(x + 1.4, y - lh * 0.6, t, ha="left", va="top", fontsize=fs,
            color=PALETA["texto"], zorder=6, linespacing=1.3)


def leyenda(ax, elementos, x, y, fs=7.8, dy=2.6, ancho=40):
    """Leyenda manual: elementos = [(color, borde, etiqueta), ...]."""
    for i, (fc, ec, txt) in enumerate(elementos):
        yy = y - i * dy
        ax.add_patch(Rectangle((x, yy), 2.6, 1.7, fc=fc, ec=ec, lw=1.0, zorder=5))
        ax.text(x + 3.8, yy + 0.85, txt, va="center", fontsize=fs,
                color=PALETA["texto"], zorder=5)


def guardar(fig, nombre, dpi=200):
    """Guarda el diagrama en la carpeta diagramas/."""
    ruta = os.path.join(DIR_DIAG, nombre)
    fig.savefig(ruta, dpi=dpi, bbox_inches="tight", pad_inches=0.16,
                facecolor="white")
    plt.close(fig)
    print(f"  ok  {nombre}")
    return ruta
