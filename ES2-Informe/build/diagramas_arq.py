"""Diagramas de arquitectura: contexto, casos de uso y vistas 4+1 (lógica, desarrollo, procesos, física)."""
import os
import sys
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dib import (PALETA, guardar, lienzo, caja, caja_izq, elipse, actor, flecha,
                 titulo, banda, contenedor, leyenda, nota, linea)


# --------------------------------------------------------------------------- #
# 05. Contexto (C4 nivel 1)
# --------------------------------------------------------------------------- #
def diagrama_contexto():
    fig, ax = lienzo(15.2, 8.8, 100, 100)
    titulo(ax, "Contexto del sistema (C4 — nivel 1)", y=99,
           sub="Quién usa la plataforma y con qué sistemas externos se comunica")

    caja(ax, 33, 40, 34, 17,
         "SISTEMA WEB DE MONITOREO\nY TRAZABILIDAD DEL TREFILADO\n[Software a construir]",
         color=PALETA["verde_p"], borde=PALETA["verde"], bold=True, fs=10.5, wrap=None, lw=2.2)

    caja_izq(ax, 2, 70, 24, 11, "Operador de línea",
             "Consulta el resultado de la última inspección y su estado",
             color=PALETA["azul_p"], borde=PALETA["azul"], fs=9, fs_sub=7.2)
    caja_izq(ax, 2, 47, 24, 11, "Supervisor de calidad",
             "Analiza históricos, tendencias e indicadores por lote",
             color=PALETA["azul_p"], borde=PALETA["azul"], fs=9, fs_sub=7.2)
    caja_izq(ax, 2, 24, 24, 11, "Administrador",
             "Gestiona usuarios, roles y parámetros de recetas",
             color=PALETA["azul_p"], borde=PALETA["azul"], fs=9, fs_sub=7.2)

    caja_izq(ax, 74, 70, 24, 11, "Sistema de captura de planta\n(APP-AZA / simulador)",
             "Envía la medición angular de cada ráfaga ya procesada",
             color=PALETA["morado_p"], borde=PALETA["morado"], fs=9, fs_sub=7.2)
    caja_izq(ax, 74, 47, 24, 11, "Servicio SMTP",
             "Entrega las notificaciones y alertas por correo",
             color=PALETA["gris_p"], borde=PALETA["gris_m"], fs=9, fs_sub=7.2)
    caja_izq(ax, 74, 24, 24, 11, "Almacenamiento de objetos (S3)",
             "Respaldo cifrado de imágenes y exportaciones",
             color=PALETA["gris_p"], borde=PALETA["gris_m"], fs=9, fs_sub=7.2)

    flecha(ax, (26, 75.5), (33, 56), color=PALETA["azul"], lw=1.8, rad=0.12)
    flecha(ax, (26, 52.5), (33, 49), color=PALETA["azul"], lw=1.8)
    flecha(ax, (26, 29.5), (33, 43), color=PALETA["azul"], lw=1.8, rad=-0.12)
    ax.text(22, 62, "HTTPS\nnavegador", fontsize=7.2, color=PALETA["azul"], ha="center")

    flecha(ax, (74, 75.5), (67, 56), color=PALETA["morado"], lw=1.8, rad=-0.12)
    ax.text(74, 65.5, "REST / HTTPS\n(token de servicio)", fontsize=7.2,
            color=PALETA["morado"], ha="center")
    flecha(ax, (67, 44), (74, 52), color=PALETA["gris_m"], lw=1.6, ls=(0, (4, 3)))
    ax.text(70.5, 44.5, "SMTP", fontsize=7.2, color=PALETA["gris_m"], ha="center")
    flecha(ax, (67, 41), (74, 29.5), color=PALETA["gris_m"], lw=1.6, ls=(0, (4, 3)))
    ax.text(70.5, 32.5, "S3 API", fontsize=7.2, color=PALETA["gris_m"], ha="center")

    nota(ax, 33, 33, "El sistema NO procesa imágenes ni se conecta a la maquinaria: recibe la "
                     "medición ya calculada (dato simulado o enviado por la app de planta), la "
                     "valida, la persiste y la publica.", w=52, ancho=47, fs=7.4)
    return guardar(fig, "05_contexto_c4.png")


# --------------------------------------------------------------------------- #
# 06. Casos de uso (UML)
# --------------------------------------------------------------------------- #
def diagrama_casos_uso():
    fig, ax = lienzo(15.6, 9.4, 100, 100)
    titulo(ax, "Diagrama de casos de uso del sistema", y=99,
           sub="Cada actor se ubica en la fila de los casos de uso que le corresponden")

    ax.add_patch(Rectangle((16, 5), 76, 86, fc="#FAFAFA", ec=PALETA["gris_m"],
                           lw=1.4, zorder=1))
    ax.text(54, 89.6, "Sistema Web de Monitoreo y Trazabilidad", ha="center",
            va="top", fontsize=9.6, color=PALETA["gris"], weight="bold")

    filas = [
        (84, "Operador\nde planta", ["UC-01\nIniciar sesión", "UC-02\nVer última inspección\ny alerta temprana",
                                     "UC-03\nConsultar historial\nde 24 horas"]),
        (62, "Supervisor de\nproducción", ["UC-04\nDashboard de\nindicadores", "UC-05\nHistórico con\nfiltros y exportación",
                                           "UC-06\nTrazabilidad\nde lote"]),
        (40, "Administrador\ndel sistema", ["UC-07\nGestionar usuarios\ny roles", "UC-08\nGestionar recetas,\nlotes y batches",
                                            "UC-09\nConfigurar\nparámetros"]),
        (18, "Sistema de\nvisión artificial", ["UC-10\nRegistrar\ninspección", "UC-11\nEvaluar estado\npor tolerancia",
                                               "UC-12\nGenerar y\nenviar reportes"]),
    ]
    xs = [30, 54, 78]
    W, H = 19, 9
    for y, nombre_actor, casos in filas:
        actor(ax, 7, y, nombre_actor, escala=0.82)
        for x, caso in zip(xs, casos):
            elipse(ax, x, y, W, H, caso, fs=7.2, wrap=None)
            flecha(ax, (7, y), (x - W / 2, y), color=PALETA["gris"], lw=1.1,
                   estilo="-", size=1, zorder=1.5)

    # relaciones entre casos de uso
    flecha(ax, (30 + W / 2, 18), (54 - W / 2, 18), color=PALETA["gris_m"], lw=1.2,
           ls=(0, (5, 3)))
    ax.text(42, 19.3, "«include»", ha="center", va="bottom", fontsize=7.2,
            color=PALETA["gris_m"])
    flecha(ax, (78 - W / 2, 62), (54 + W / 2, 62), color=PALETA["gris_m"], lw=1.2,
           ls=(0, (5, 3)))
    ax.text(66, 63.3, "«extend»", ha="center", va="bottom", fontsize=7.2,
            color=PALETA["gris_m"])

    actor(ax, 96, 18, "Servicio\nSMTP", escala=0.82)
    flecha(ax, (78 + W / 2, 18), (96, 18), color=PALETA["gris"], lw=1.1,
           estilo="-", size=1)

    ax.text(54, 7.4, "Los cuatro actores requieren autenticación previa (UC-01); el Área de calidad "
                     "comparte UC-04 y UC-05 con el supervisor.",
            ha="center", fontsize=7.0, color=PALETA["gris_m"], style="italic")
    return guardar(fig, "06_casos_uso.png")


# --------------------------------------------------------------------------- #
# 07. Vista lógica
# --------------------------------------------------------------------------- #
def diagrama_vista_logica():
    fig, ax = lienzo(15.6, 9.6, 100, 100)
    titulo(ax, "Vista lógica — componentes y capas", y=99,
           sub="Arquitectura en capas con dependencias unidireccionales hacia el dominio")

    banda(ax, 2, 88, 96, 6.5, "CLIENTE  ·  SPA React + Tailwind (navegador del operador y del supervisor)",
          color=PALETA["azul_p"], tc=PALETA["azul"], fs=8.2)

    componentes = [
        ("Capa de presentación\n(React SPA)",
         "Pages: Login, Dashboard, Histórico,\nDetalle, Recetas, Usuarios\nHooks + Context de sesión",
         PALETA["azul_p"], PALETA["azul"], 2, 66, 21, 18),
        ("API REST\n(FastAPI)",
         "Routers por dominio, validación\nPydantic, JWT, rate limit,\nOpenAPI 3.1",
         PALETA["verde_p"], PALETA["verde"], 26, 66, 21, 18),
        ("Capa de servicios\n(dominio)",
         "Reglas de negocio: tolerancias,\nestado, indicadores, alertas,\nauditoría",
         PALETA["amarillo_p"], PALETA["amarillo"], 50, 66, 22, 18),
        ("Capa de acceso a datos\n(repositorios)",
         "SQLAlchemy 2.0 + migraciones\nAlembic, patrón repositorio,\ntransacciones",
         PALETA["rojo_p"], PALETA["rojo"], 75, 66, 23, 18),
    ]
    for t, s, fc, ec, x, y, w, h in componentes:
        caja_izq(ax, x, y, w, h, t, s, color=fc, borde=ec, fs=8.2, fs_sub=7.0,
                 wrap_t=24, wrap_s=30)

    almacenes = [
        ("PostgreSQL 16", "Datos estructurados:\nusuarios, recetas, lotes,\ninspecciones, auditoría",
         PALETA["verde_p"], PALETA["verde"], 26, 42, 21, 14),
        ("MinIO / S3", "Imágenes de ráfaga y\nexportaciones (no\ne structurado)",
         PALETA["gris_p"], PALETA["gris_m"], 50, 42, 22, 14),
        ("Redis", "Caché de indicadores\ny cola de alertas",
         PALETA["rojo_p"], PALETA["rojo"], 75, 42, 23, 14),
    ]
    for t, s, fc, ec, x, y, w, h in almacenes:
        caja_izq(ax, x, y, w, h, t, s, color=fc, borde=ec, fs=8.2, fs_sub=6.9,
                 wrap_t=24, wrap_s=32)

    # flujo principal
    for x1, x2 in [(23, 26), (47, 50), (72, 75)]:
        flecha(ax, (x1, 75), (x2, 75), color=PALETA["gris"], lw=1.6)
    for x, w in [(28.5, 21), (52.5, 22), (77.5, 23)]:
        pass

    banda(ax, 2, 30, 96, 7.5,
          "SERVICIOS TRANSVERSALES  ·  configuración por entorno · logging estructurado · "
          "métricas · manejo centralizado de errores",
          color=PALETA["gris_p"], tc=PALETA["gris"], fs=8.0)

    caja_izq(ax, 2, 10, 30, 15, "Trabajador asíncrono\n(Celery / RQ)",
             "Genera exportaciones, calcula\nagregados y despacha alertas\nfuera del ciclo de la petición",
             color=PALETA["morado_p"], borde=PALETA["morado"], fs=8.2, fs_sub=6.9,
             wrap_t=24, wrap_s=32)
    caja_izq(ax, 34, 10, 30, 15, "Seguridad transversal",
             "Autenticación JWT, RBAC,\nvalidación de entrada, cifrado\nde respaldos y auditoría",
             color=PALETA["azul_p"], borde=PALETA["azul"], fs=8.2, fs_sub=6.9,
             wrap_t=24, wrap_s=32)
    caja_izq(ax, 66, 10, 32, 15, "Observabilidad",
             "Health checks, trazas por\ncorrelación, alertas de error\ny tablero de disponibilidad",
             color=PALETA["gris_p"], borde=PALETA["gris_m"], fs=8.2, fs_sub=6.9,
             wrap_t=24, wrap_s=32)

    flecha(ax, (36.5, 66), (36.5, 56), color=PALETA["rojo"], lw=1.5, ls=(0, (4, 3)))
    flecha(ax, (61, 66), (61, 56), color=PALETA["rojo"], lw=1.5, ls=(0, (4, 3)))
    flecha(ax, (86.5, 66), (86.5, 56), color=PALETA["rojo"], lw=1.5, ls=(0, (4, 3)))
    ax.text(63.4, 60.5, "async", fontsize=6.8, color=PALETA["rojo"], rotation=90, va="center")
    return guardar(fig, "07_vista_logica.png")


# --------------------------------------------------------------------------- #
# 08. Vista de desarrollo
# --------------------------------------------------------------------------- #
def diagrama_vista_desarrollo():
    fig, ax = lienzo(15.4, 9.8, 100, 100)
    titulo(ax, "Vista de desarrollo — organización del repositorio", y=99,
           sub="Monorepo con dos aplicaciones y módulos compartidos; ramas por historia de usuario")

    raiz = "\n".join([
        "aza-web/                       repositorio monorepo",
        "|-- backend/",
        "|   |-- app/",
        "|   |   |-- api/          routers por dominio (auth, recetas, lotes, inspecciones)",
        "|   |   |-- core/         config, seguridad, dependencias, errores",
        "|   |   |-- models/       entidades SQLAlchemy + migraciones Alembic",
        "|   |   |-- repositories/ acceso a datos (patron repositorio)",
        "|   |   |-- schemas/      DTO Pydantic (entrada y salida)",
        "|   |   `-- services/     reglas de negocio e indicadores",
        "|   `-- tests/            unitarias, integracion, rendimiento",
        "|-- frontend/",
        "|   |-- src/pages/        Login, Dashboard, Historico, Detalle, Recetas, Usuarios",
        "|   |-- src/components/   tablas, filtros, tarjetas KPI, graficos",
        "|   |-- src/services/     cliente API tipado (fetch + tipos TS)",
        "|   `-- src/styles/       tokens de diseno y tema Tailwind",
        "|-- infra/",
        "|   |-- docker-compose.yml    api, db, minio, redis, worker, proxy",
        "|   `-- .github/workflows/    CI: lint, tests, build, deploy",
        "`-- docs/                 arquitectura, ADR, manual de operacion",
    ])
    ax.add_patch(Rectangle((2, 8), 62, 84, fc="#FAFAFA", ec=PALETA["gris_m"], lw=1.2,
                           zorder=1))
    ax.text(4, 89, raiz, ha="left", va="top", fontsize=7.0,
            family="DejaVu Sans Mono", color=PALETA["texto"], zorder=3,
            linespacing=1.62)
    ax.text(4, 10.4, "Cada rama sigue la convención  feature/HU-<n>-<descripcion>  y se "
                     "integra por pull request revisado.",
            ha="left", va="bottom", fontsize=7.0, color=PALETA["gris_m"], style="italic")

    capas = [
        ("presentacion/*", "Depende de servicios.\nNunca contiene SQL.", PALETA["azul_p"], PALETA["azul"]),
        ("servicios/*", "Contiene las reglas de negocio.\nNo conoce HTTP ni SQL.", PALETA["amarillo_p"], PALETA["amarillo"]),
        ("repositorios/*", "Único lugar con SQL.\nDevuelve modelos de dominio.", PALETA["rojo_p"], PALETA["rojo"]),
        ("modelos/*", "Sin dependencias hacia arriba.\nBase de todas las capas.", PALETA["verde_p"], PALETA["verde"]),
    ]
    ax.text(68, 89, "Regla de dependencia", fontsize=9.2, weight="bold", color=PALETA["gris"])
    for i, (t, s, fc, ec) in enumerate(capas):
        caja_izq(ax, 66, 68 - i * 15.5, 32, 13, t, s, color=fc, borde=ec,
                 fs=8.0, fs_sub=6.9, wrap_t=26, wrap_s=34)

    for i in range(3):
        y1 = 68 - i * 15.5
        flecha(ax, (82, y1), (82, y1 - 2.5), color=PALETA["gris"], lw=1.4)
    ax.text(66, 8.5, "Una capa solo puede depender de la inmediatamente inferior.",
            fontsize=7.2, color=PALETA["gris_m"], style="italic")
    return guardar(fig, "08_vista_desarrollo.png")


# --------------------------------------------------------------------------- #
# 09. Vista de procesos
# --------------------------------------------------------------------------- #
def diagrama_vista_procesos():
    fig, ax = lienzo(15.6, 9.6, 100, 100)
    titulo(ax, "Vista de procesos — secuencia «registrar inspección»", y=99,
           sub="Flujo síncrono de una petición de registro y trabajo asíncrono de alertas")

    lifelines = [
        ("Navegador\n(React)", 10, PALETA["azul"], PALETA["azul_p"]),
        ("API\n(FastAPI)", 32, PALETA["verde"], PALETA["verde_p"]),
        ("Servicio\nInspección", 54, PALETA["amarillo"], PALETA["amarillo_p"]),
        ("Repositorio", 74, PALETA["rojo"], PALETA["rojo_p"]),
        ("PostgreSQL", 91, PALETA["gris"], PALETA["gris_p"]),
    ]
    top = 84
    for nombre, x, ec, fc in lifelines:
        caja(ax, x - 8, top, 16, 8, nombre, color=fc, borde=ec, fs=7.8, bold=True,
             wrap=None, radio=0.5)
        ax.plot([x, x], [top, 12], color=PALETA["gris_m"], lw=1.0, ls=(0, (4, 3)), zorder=1)

    y = top - 4

    def msg(y, x1, x2, texto, color=None, async_=False, n=None):
        color = color or PALETA["gris"]
        estilo = "-|>" if not async_ else "-|>"
        flecha(ax, (x1, y), (x2, y), color=color, lw=1.5, estilo=estilo, size=10,
               ls="-" if not async_ else (0, (5, 3)))
        pref = f"{n}. " if n else ""
        ax.text((x1 + x2) / 2, y + 1.1, pref + texto, ha="center", va="bottom",
                fontsize=7.2, color=color, zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.9))

    pasos = [
        (78, 10, 32, "POST /api/v1/inspecciones + JWT", 1),
        (72, 32, 54, "registrar(dto)", 2),
        (66, 54, 74, "obtener_receta_vigente(receta_id)", 3),
        (60, 74, 91, "SELECT … WHERE activa = true", 4),
        (54, 91, 74, "fila de receta", 5),
        (48, 74, 54, "receta", 6),
        (42, 54, 74, "insertar(inspeccion, estado_calculado)", 7),
        (36, 74, 91, "INSERT + auditoría", 8),
        (30, 54, 32, "inspección registrada", 9),
        (24, 32, 10, "201 Created { id, estado }", 10),
    ]
    for yy, x1, x2, txt, n in pasos:
        color = PALETA["gris_m"] if n in (5, 6, 9, 10) else PALETA["gris"]
        msg(yy, x1, x2, txt, color=color, async_=n in (5, 6, 9, 10), n=n)

    ax.text(54, 45.5, "el estado se calcula con los límites\nde la receta vigente",
            fontsize=6.9, color=PALETA["amarillo"], ha="center", va="center",
            style="italic")

    # bloque asíncrono
    ax.add_patch(Rectangle((28, 12), 66, 9.5, fc=PALETA["morado_p"], ec=PALETA["morado"],
                           lw=1.2, ls=(0, (5, 3)), zorder=1, alpha=0.55))
    ax.text(61, 18.6, "[asíncrono] el servicio encola la alerta y responde sin esperar al correo",
            ha="center", va="center", fontsize=7.2, color=PALETA["morado"], style="italic")
    ax.text(61, 14.9, "El trabajador toma la tarea de Redis, envía el correo por SMTP y "
                      "marca la alerta como notificada",
            ha="center", va="center", fontsize=6.9, color=PALETA["morado"])

    ax.text(2, 7.5, "Tiempo de respuesta objetivo: p95 < 300 ms (sin contar el envío de correo, "
                    "que ocurre fuera de la petición).",
            fontsize=7.4, color=PALETA["gris"], style="italic")
    return guardar(fig, "09_vista_procesos.png")


# --------------------------------------------------------------------------- #
# 10. Vista física
# --------------------------------------------------------------------------- #
def diagrama_vista_fisica():
    fig, ax = lienzo(15.6, 9.8, 100, 100)
    titulo(ax, "Vista física — despliegue en la nube", y=99,
           sub="Contenedores Docker sobre un VPS, respaldo externo y pipeline CI/CD")

    # cliente
    contenedor(ax, 2, 62, 20, 26, "Cliente", color=PALETA["azul"])
    caja(ax, 4, 72, 16, 11, "Navegador\n(desktop / tablet)", color=PALETA["azul_p"],
         borde=PALETA["azul"], fs=7.6, bold=True, wrap=None)
    caja(ax, 4, 64, 16, 7, "Red LAN / Internet", color="white", borde=PALETA["gris_m"],
         fs=7.0, wrap=None)

    # VPS
    contenedor(ax, 26, 8, 50, 80, "VPS en la nube  ·  Ubuntu 24.04  ·  Docker Compose",
               color=PALETA["verde"])
    caja(ax, 28, 72, 46, 12, "nginx  ·  TLS 1.3  ·  reverse proxy  ·  rate limit",
         color=PALETA["verde_p"], borde=PALETA["verde"], fs=7.8, bold=True, wrap=None)
    caja(ax, 28, 58, 22, 11, "Contenedor\napi (FastAPI)\n:8000", color=PALETA["azul_p"],
         borde=PALETA["azul"], fs=7.4, bold=True, wrap=None)
    caja(ax, 52, 58, 22, 11, "Contenedor\nworker\n(Celery)", color=PALETA["morado_p"],
         borde=PALETA["morado"], fs=7.4, bold=True, wrap=None)
    caja(ax, 28, 44, 22, 11, "Contenedor\nfrontend\n(React build)", color=PALETA["azul_p"],
         borde=PALETA["azul"], fs=7.4, bold=True, wrap=None)
    caja(ax, 52, 44, 22, 11, "Contenedor\nredis\n:caché y cola", color=PALETA["rojo_p"],
         borde=PALETA["rojo"], fs=7.4, bold=True, wrap=None)
    caja(ax, 28, 28, 22, 12, "PostgreSQL 16\nvolumen persistente\n:5432", color=PALETA["verde_p"],
         borde=PALETA["verde"], fs=7.4, bold=True, wrap=None)
    caja(ax, 52, 28, 22, 12, "MinIO\nvolumen persistente\n:9000", color=PALETA["gris_p"],
         borde=PALETA["gris_m"], fs=7.4, bold=True, wrap=None)
    caja(ax, 28, 12, 46, 11, "Volumen /var/aza  ·  respaldos diarios cifrados  ·  retención 30 días",
         color=PALETA["amarillo_p"], borde=PALETA["amarillo"], fs=7.4, bold=True, wrap=None)

    # externos
    contenedor(ax, 80, 62, 18, 26, "Servicios externos", color=PALETA["gris_m"])
    caja(ax, 82, 72, 14, 10, "GitHub\nActions (CI/CD)", color=PALETA["gris_p"],
         borde=PALETA["gris_m"], fs=7.2, bold=True, wrap=None)
    caja(ax, 82, 64, 14, 7, "SMTP\ncorreo", color=PALETA["gris_p"], borde=PALETA["gris_m"],
         fs=7.2, bold=True, wrap=None)

    contenedor(ax, 80, 26, 18, 22, "Respaldo", color=PALETA["gris_m"])
    caja(ax, 82, 30, 14, 14, "Bucket S3\n(cifrado,\nregión distinta)", color=PALETA["gris_p"],
         borde=PALETA["gris_m"], fs=7.2, bold=True, wrap=None)

    flecha(ax, (22, 76), (28, 78), color=PALETA["azul"], lw=1.8,
           etiqueta="HTTPS 443", dy=2.4, fs=6.9)
    flecha(ax, (76, 70), (82, 76), color=PALETA["gris_m"], lw=1.5, ls=(0, (4, 3)),
           etiqueta="deploy", dy=2.2, fs=6.9)
    flecha(ax, (76, 64), (82, 67), color=PALETA["gris_m"], lw=1.5, ls=(0, (4, 3)),
           etiqueta="SMTP", dy=-2.0, fs=6.9)
    flecha(ax, (76, 40), (82, 36), color=PALETA["gris_m"], lw=1.5, ls=(0, (4, 3)),
           etiqueta="backup", dy=2.2, fs=6.9)

    ax.text(2, 50, "Escalabilidad:\nla API y el worker\nescalan en réplicas\nsin cambiar el\nmodelo de datos.",
            fontsize=7.2, color=PALETA["gris"], va="top", linespacing=1.4)
    return guardar(fig, "10_vista_fisica.png")


if __name__ == "__main__":
    print("Generando diagramas de arquitectura...")
    diagrama_contexto()
    diagrama_casos_uso()
    diagrama_vista_logica()
    diagrama_vista_desarrollo()
    diagrama_vista_procesos()
    diagrama_vista_fisica()
    print("Listo.")
