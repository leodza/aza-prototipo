"""Diagramas de datos y calidad: DER, pirámide de pruebas y capas de seguridad."""
import os
import sys
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dib import (PALETA, guardar, lienzo, caja, caja_izq, flecha, titulo,
                 banda, contenedor, leyenda, nota, linea)


# --------------------------------------------------------------------------- #
# 11. DER
# --------------------------------------------------------------------------- #
def entidad(ax, x, y, w, nombre, campos, color, borde, fs=6.6, alto_fila=3.0):
    """Dibuja una entidad del DER. Devuelve (x, y, w, h)."""
    h_cab = 4.6
    h = h_cab + len(campos) * alto_fila
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=borde, lw=1.4, zorder=2))
    ax.add_patch(Rectangle((x, y + h - h_cab), w, h_cab, fc=borde, ec=borde, lw=1.4, zorder=3))
    ax.text(x + w / 2, y + h - h_cab / 2, nombre, ha="center", va="center",
            fontsize=7.6, color="white", weight="bold", zorder=4)
    for i, campo in enumerate(campos):
        yy = y + h - h_cab - 1.5 - i * alto_fila
        ax.text(x + 1.0, yy, campo, ha="left", va="center", fontsize=fs,
                color=PALETA["texto"], zorder=4,
                family="DejaVu Sans Mono" if campo[:2] in ("PK", "FK", "UK") else "DejaVu Sans")
    return (x, y, w, h)


def diagrama_der():
    fig, ax = lienzo(16.2, 11.2, 100, 100)
    titulo(ax, "Modelo entidad-relación del sistema (modelo lógico normalizado, 3FN)", y=99.4,
           sub="Claves primarias (PK), claves foráneas (FK) y restricciones de unicidad (UK)")

    azul, verde, rojo, morado, gris = (PALETA["azul"], PALETA["verde"], PALETA["rojo"],
                                       PALETA["morado"], PALETA["gris_m"])

    entidad(ax, 1, 78, 21, "roles",
            ["PK  id", "UK  nombre", "    descripcion"], azul, azul)
    entidad(ax, 1, 48, 21, "usuarios",
            ["PK  id", "UK  username", "    pin_hash", "    rol_id  FK", "    activo", "    creado_en"], azul, azul)
    entidad(ax, 1, 24, 21, "sesiones",
            ["PK  id", "    usuario_id FK", "    refresh_hash", "    expira_en", "    revocado"], azul, azul)

    entidad(ax, 25, 66, 21, "recetas",
            ["PK  id", "UK  nombre", "    min_tol", "    max_tol", "    activa", "    creado_por FK", "    creado_en"], verde, verde)
    entidad(ax, 25, 40, 21, "lotes",
            ["PK  id", "UK  codigo", "    receta_id FK", "    fecha_inicio", "    fecha_fin", "    turno"], verde, verde)
    entidad(ax, 25, 16, 21, "batches",
            ["PK  id", "    lote_id FK", "    numero", "    iniciado_en"], verde, verde)

    entidad(ax, 49, 34, 24, "inspecciones",
            ["PK  id", "    fecha_hora", "    receta_id FK", "    lote_id FK", "    batch_id FK",
             "    operador_id FK", "    angulo", "    limite_min", "    limite_max",
             "    estado", "    observacion", "    origen", "    creado_en"], rojo, rojo)

    entidad(ax, 76, 64, 22, "imagenes",
            ["PK  id", "    inspeccion_id FK", "    objeto_key", "    tamano_bytes", "    sha256", "    capturada_en"], gris, gris)
    entidad(ax, 76, 40, 22, "alarmas",
            ["PK  id", "    inspeccion_id FK", "    tipo", "    severidad", "    notificada", "    creada_en"], morado, morado)
    entidad(ax, 76, 8, 22, "auditoria",
            ["PK  id", "    usuario_id FK", "    accion", "    entidad", "    entidad_id",
             "    fecha", "    ip", "    detalle (JSONB)"], morado, morado)

    def rel(p1, p2, card1="1", card2="N", color=None, puntos=None):
        color = color or PALETA["gris"]
        pts = [p1] + (puntos or []) + [p2]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color=color, lw=1.3, zorder=1.5)
        ax.plot([p2[0]], [p2[1]], marker="o", markersize=3.5, color=color, zorder=2.5)

        tramos = []
        total = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            d = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            tramos.append((a, b, d))
            total += d

        def punto_en(f):
            objetivo = total * f
            acum = 0.0
            for a, b, d in tramos:
                if acum + d >= objetivo or d == 0:
                    k = 0.0 if d == 0 else (objetivo - acum) / d
                    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
                acum += d
            return pts[-1]

        for f, etiqueta in ((0.34, card1), (0.72, card2)):
            px, py = punto_en(f)
            ax.text(px, py, etiqueta, fontsize=7.2, color=color, weight="bold",
                    ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.95))

    rel((11.5, 78), (11.5, 67.6), "1", "N")            # roles -> usuarios
    rel((11.5, 48), (11.5, 40.6), "1", "N")            # usuarios -> sesiones
    rel((35.5, 66), (35.5, 59.6), "1", "N")            # recetas -> lotes
    rel((35.5, 40), (35.5, 32.6), "1", "N")            # lotes -> batches
    rel((46, 78), (49, 71.6), "1", "N")                # recetas -> inspecciones
    rel((46, 52), (49, 52), "1", "N")                  # lotes -> inspecciones
    rel((46, 22), (49, 38), "1", "N")                  # batches -> inspecciones
    rel((22, 63), (49, 63), "1", "N")                  # usuarios -> inspecciones
    rel((73, 66), (76, 70), "1", "N")                  # inspecciones -> imagenes
    rel((73, 50), (76, 50), "1", "N")                  # inspecciones -> alarmas
    rel((22, 53), (76, 12), "1", "N", puntos=[(23.6, 53), (23.6, 12)])  # usuarios -> auditoria

    ax.text(1, 17.5, "Cardinalidad 1:N en todas las\nrelaciones. Integridad referencial:\n"
                     "ON DELETE RESTRICT en los\nmaestros y ON DELETE CASCADE\nsolo en sesiones e imágenes.",
            fontsize=6.9, color=PALETA["gris"], style="italic", va="top", linespacing=1.35)
    leyenda(ax, [
        ("white", PALETA["gris"], "PK clave primaria · FK foránea · UK única"),
        ("white", PALETA["gris"], "detalle (JSONB) = dato semiestructurado"),
    ], x=1, y=5.6, dy=2.8, fs=6.9)
    return guardar(fig, "11_der.png")


# --------------------------------------------------------------------------- #
# 12. Pirámide de pruebas
# --------------------------------------------------------------------------- #
def diagrama_piramide():
    fig, ax = lienzo(14.4, 9.0, 100, 100)
    titulo(ax, "Estrategia de pruebas: pirámide y cobertura por nivel", y=99,
           sub="Qué se automatiza, con qué herramienta y qué se valida manualmente")

    niveles = [
        (24, 36, 40, 28, "Unitarias  ·  112 casos",
         "pytest (servicios y reglas) + Vitest (componentes React)",
         "Cálculo de estado, tolerancias, indicadores y validaciones",
         PALETA["verde"], PALETA["verde_p"]),
        (40, 28, 52, 20, "Integración y sistema  ·  28 casos",
         "pytest + httpx + Testcontainers (PostgreSQL real)",
         "Contratos de API, permisos y transacciones",
         PALETA["naranja"], PALETA["naranja_p"]),
        (52, 20, 62, 13, "Rendimiento  ·  6 escenarios",
         "k6 (carga) + EXPLAIN ANALYZE en PostgreSQL",
         "p95 < 300 ms con 50 usuarios concurrentes",
         PALETA["morado"], PALETA["morado_p"]),
        (62, 13, 70, 7, "UAT  ·  4 escenarios",
         "Checklist manual guiado (PO + planta)",
         "Flujo completo y utilidad real",
         PALETA["rojo"], PALETA["rojo_p"]),
    ]
    for y_inf, hw_inf, y_sup, hw_sup, t, herr, crit, color, claro in niveles:
        pts = [(50 - hw_inf, y_inf), (50 + hw_inf, y_inf),
               (50 + hw_sup, y_sup), (50 - hw_sup, y_sup)]
        ax.add_patch(Polygon(pts, closed=True, fc=claro, ec=color, lw=1.6, zorder=2))
        h = y_sup - y_inf
        d = h / 3.4
        fs_t = 8.0 if h >= 12 else 7.0
        fs_s = 6.7 if h >= 12 else 6.2
        ax.text(50, y_sup - d * 0.55, t, ha="center", va="center", fontsize=fs_t,
                weight="bold", color=PALETA["texto"], zorder=4)
        ax.text(50, y_sup - d * 1.45, textwrap.fill(herr, 46), ha="center", va="center",
                fontsize=fs_s, color=color, zorder=4, style="italic", linespacing=1.2)
        ax.text(50, y_sup - d * 2.35, textwrap.fill(crit, 44), ha="center", va="center",
                fontsize=fs_s, color=PALETA["gris"], zorder=4, linespacing=1.2)

    ax.annotate("", xy=(6.5, 72), xytext=(6.5, 22),
                arrowprops=dict(arrowstyle="-|>", color=PALETA["gris"], lw=1.5))
    ax.text(3.4, 47, "Nivel de abstracción  →", rotation=90, va="center", ha="center",
            fontsize=8.2, color=PALETA["gris"], weight="bold")

    ax.text(2, 14, "Meta de cobertura: ≥ 80 % en la capa de servicios y ≥ 70 % global.",
            fontsize=7.6, color=PALETA["gris"], style="italic")
    ax.text(2, 10, "Cada caso automatizado referencia un RF y un caso de uso; la trazabilidad "
                   "completa está en el Anexo C.",
            fontsize=7.6, color=PALETA["gris"], style="italic")
    ax.text(2, 6, "Las pruebas unitarias y de integración se ejecutan en cada push (CI); las de "
                  "rendimiento, antes de cada entrega.",
            fontsize=7.6, color=PALETA["gris"], style="italic")
    return guardar(fig, "12_piramide_pruebas.png")


# --------------------------------------------------------------------------- #
# 13. Capas de seguridad
# --------------------------------------------------------------------------- #
def diagrama_seguridad():
    fig, ax = lienzo(15.4, 9.2, 100, 100)
    titulo(ax, "Defensa en profundidad: capas de control y amenazas mitigadas", y=99,
           sub="Cada capa se justifica por las amenazas que detiene (categorías STRIDE / OWASP Top 10)")

    capas = [
        ("1. Red y perímetro", "TLS 1.3 obligatorio, firewall con puertos mínimos, rate limit, "
                               "WAF básico, bloqueo por intentos fallidos",
         "Spoofing · Denegación de servicio", PALETA["azul"], PALETA["azul_p"]),
        ("2. Aplicación y sesión", "Login con PIN y hash Argon2id, JWT de acceso corto + refresh "
                                   "rotatorio, RBAC por rol, validación Pydantic, CSRF y CORS",
         "Elevación de privilegios · Suplantación", PALETA["verde"], PALETA["verde_p"]),
        ("3. Datos y respaldo", "Cifrado en reposo del volumen, respaldo diario cifrado en S3, "
                                "principio de mínimo privilegio en la BD, bitácora de auditoría",
         "Manipulación de datos · Pérdida de información", PALETA["amarillo"], PALETA["amarillo_p"]),
        ("4. Operación y desarrollo", "Secretos fuera del código, dependencias fijadas y auditadas, "
                                      "SAST + revisión por PR, parcheo mensual, logs sin datos sensibles",
         "Fuga de credenciales · Dependencias vulnerables", PALETA["morado"], PALETA["morado_p"]),
    ]
    for i, (t, d, amenaza, color, claro) in enumerate(capas):
        y = 74 - i * 15
        ax.add_patch(FancyBboxPatch((12, y), 60, 12, boxstyle="round,pad=0,rounding_size=0.8",
                                    fc=claro, ec=color, lw=1.6, zorder=2))
        ax.text(13.6, y + 8.6, t, fontsize=8.6, weight="bold", color=color, va="center", zorder=3)
        ax.text(13.6, y + 4.2, textwrap.fill(d, 72), fontsize=7.0, color=PALETA["texto"],
                va="center", zorder=3, linespacing=1.3)
        ax.text(75, y + 6, textwrap.fill(amenaza, 22), fontsize=7.2, color=color,
                va="center", zorder=3, style="italic")

    ax.text(75, 89, "Amenazas\nmitigadas", fontsize=8.4, weight="bold", color=PALETA["gris"],
            va="center", ha="left", linespacing=1.3)

    ax.text(2, 12.5, "Un atacante debe superar las cuatro capas: ninguna controla sola la seguridad "
                     "del sistema.", fontsize=7.4, color=PALETA["gris"], style="italic")
    ax.text(2, 8.5, "El detalle de cada amenaza y su medida concreta está en la Tabla 21 "
                    "(sección 2.1.5.11).", fontsize=7.4, color=PALETA["gris"], style="italic")
    return guardar(fig, "13_capas_seguridad.png")


if __name__ == "__main__":
    print("Generando diagramas de datos y calidad...")
    diagrama_der()
    diagrama_piramide()
    diagrama_seguridad()
    print("Listo.")
