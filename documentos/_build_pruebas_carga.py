# -*- coding: utf-8 -*-
"""Genera el Informe de Pruebas de Carga del prototipo AZA."""
import json
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "App-Funcional")
EVID = os.path.join(APP, "evidencias")
PRUEBAS = os.path.join(APP, "pruebas_carga")
SALIDA = os.path.join(RAIZ, "documentos", "Informe_Pruebas_de_Carga.docx")

LOCAL = json.load(open(os.path.join(PRUEBAS, "resultados.json"), encoding="utf-8"))
NUBE = json.load(open(os.path.join(PRUEBAS, "resultados_nube.json"), encoding="utf-8"))

VERDE = RGBColor(0x15, 0x4A, 0x1C)
VERDE_HEX = "154A1C"
VERDE_CLARO = "E3EFE5"
GRIS_CODIGO = "F2F4F3"
GRIS_TABLA = "EDF1F2"
TINTA = RGBColor(0x1C, 0x24, 0x27)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.1)
sec.top_margin = Cm(2.0)
sec.bottom_margin = Cm(1.9)

normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(10.5)
normal.font.color.rgb = TINTA
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12


def _estilo(nombre, tam, color, antes, despues):
    st = doc.styles[nombre]
    st.font.name = "Calibri"
    st.font.size = Pt(tam)
    st.font.bold = True
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(antes)
    st.paragraph_format.space_after = Pt(despues)
    st.paragraph_format.keep_with_next = True


_estilo("Heading 1", 15, VERDE, 16, 7)
_estilo("Heading 2", 12, RGBColor(0x1F, 0x3A, 0x28), 12, 5)


def p(texto="", size=None, bold=False, italic=False, align=None, antes=None,
      despues=None, color=None):
    par = doc.add_paragraph()
    run = par.add_run(texto)
    if size:
        run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    if align == "c":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "j":
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if antes is not None:
        par.paragraph_format.space_before = Pt(antes)
    if despues is not None:
        par.paragraph_format.space_after = Pt(despues)
    return par


def vinetas(items):
    for it in items:
        par = doc.add_paragraph(style="List Bullet")
        par.paragraph_format.space_after = Pt(2)
        if isinstance(it, tuple):
            run = par.add_run(it[0])
            run.bold = True
            par.add_run(it[1])
        else:
            par.add_run(it)


def numeros(items):
    for it in items:
        par = doc.add_paragraph(style="List Number")
        par.paragraph_format.space_after = Pt(2)
        par.add_run(it)


def _sombrear(celda, color):
    tcpr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def _borde(tabla, color="C9D4CE"):
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), color)
        borders.append(el)
    tabla._tbl.tblPr.append(borders)


def tabla(encabezados, filas, anchos=None, fuente=9, alinear_derecha=()):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borde(t)
    for i, texto in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        celda.text = ""
        par = celda.paragraphs[0]
        run = par.add_run(texto)
        run.bold = True
        run.font.size = Pt(fuente)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        par.paragraph_format.space_before = Pt(2)
        par.paragraph_format.space_after = Pt(2)
        _sombrear(celda, VERDE_HEX)
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            par = celdas[i].paragraphs[0]
            run = par.add_run(str(valor))
            run.font.size = Pt(fuente)
            par.paragraph_format.space_before = Pt(2)
            par.paragraph_format.space_after = Pt(2)
            if i in alinear_derecha:
                par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if n % 2 == 1:
                _sombrear(celdas[i], GRIS_TABLA)
    if anchos:
        for fila in t.rows:
            for i, ancho in enumerate(anchos):
                fila.cells[i].width = Cm(ancho)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def _no_partir(t):
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


def codigo(texto, titulo=None, fuente=7.5):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_partir(t)
    celda = t.rows[0].cells[0]
    celda.text = ""
    _sombrear(celda, GRIS_CODIGO)
    _borde(t, "D8E0DB")
    par = celda.paragraphs[0]
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(4)
    if titulo:
        rt = par.add_run(titulo + "\n")
        rt.bold = True
        rt.font.size = Pt(8.5)
        rt.font.color.rgb = VERDE
    run = par.add_run(texto)
    run.font.name = "Consolas"
    run.font.size = Pt(fuente)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def nota(texto, titulo="Nota"):
    t = doc.add_table(rows=1, cols=1)
    _no_partir(t)
    celda = t.rows[0].cells[0]
    celda.text = ""
    _sombrear(celda, VERDE_CLARO)
    par = celda.paragraphs[0]
    par.paragraph_format.space_before = Pt(3)
    par.paragraph_format.space_after = Pt(3)
    run = par.add_run(f"{titulo}. ")
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = VERDE
    run2 = par.add_run(texto)
    run2.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


figuras = [0]
tablas = [0]


def figura(nombre, leyenda, ancho=15.2):
    ruta = os.path.join(EVID, nombre)
    if not os.path.exists(ruta):
        print("  falta imagen:", nombre)
        return
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(8)
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.keep_with_next = True
    par.add_run().add_picture(ruta, width=Cm(ancho))
    figuras[0] += 1
    pie = doc.add_paragraph()
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = pie.add_run(f"Figura {figuras[0]}. {leyenda}")
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x60, 0x7D, 0x8B)
    pie.paragraph_format.space_after = Pt(10)


def titulo_tabla(texto):
    tablas[0] += 1
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(1)
    par.paragraph_format.keep_with_next = True
    run = par.add_run(f"Tabla {tablas[0]}. {texto}")
    run.bold = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = VERDE


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


pie_pag = sec.footer.paragraphs[0]
pie_pag.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = pie_pag.add_run("Informe de pruebas de carga · AZA Analyzer · Aceros AZA ")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(0x78, 0x90, 0x9C)
campo = OxmlElement("w:fldSimple")
campo.set(qn("w:instr"), "PAGE")
pie_pag._p.append(campo)


def n(valor, dec=1):
    return f"{valor:,.{dec}f}".replace(",", ".")


# =============================================================== PORTADA =====
p("PROYECTO INTEGRADO · INACAP SANTIAGO CENTRO", size=9, bold=True,
  color=RGBColor(0x60, 0x7D, 0x8B), antes=60, despues=2)
p("Informe de pruebas", size=27, bold=True, color=VERDE, antes=8, despues=0)
p("de carga y estrés", size=27, bold=True, color=VERDE, despues=10)
p("Rendimiento del prototipo bajo carga concurrente y comparación de motores", size=13,
  color=RGBColor(0x33, 0x4A, 0x3A), despues=26)

tabla(["Dato", "Detalle"],
      [["Proyecto", "Sistema Web de Monitoreo y Trazabilidad del Trefilado"],
       ["Cliente", "Aceros AZA · Robotic Systems Chile"],
       ["Equipo", "Leonardo Daza (PO) · José Sarabia (SM) · Daniel Paredes (QA)"],
       ["Entornos medidos", "SQLite en equipo local · PostgreSQL 16 + S3 en AWS (us-east-1)"],
       ["Fecha de ejecución", "22 de noviembre de 2026"],
       ["Herramienta", "pruebas_carga/estres.py (generador propio sobre httpx)"]],
      anchos=[4.2, 12.0], fuente=9.5)

nota("Este informe responde tres preguntas: cuánto tarda el sistema, cuánto aguanta antes de "
     "degradarse y qué motor de base de datos sostiene la concurrencia. Todas las cifras provienen "
     "de ejecuciones reales y son reproducibles con los scripts del repositorio.", "Objetivo")

salto()

# =============================================================== 1 ===========
doc.add_heading("1. Resumen de resultados", level=1)
p("La prueba cubrió cuatro escenarios —latencia por endpoint, lecturas concurrentes, escrituras "
  "concurrentes y análisis de visión— sobre dos entornos con el mismo código. No se registró un "
  "solo error en ninguna de las corridas.", align="j")

titulo_tabla("Hallazgos principales")
tabla(["Hallazgo", "Medición", "Consecuencia"],
      [["El tablero responde rápido", "8,6 ms de p95", "Adecuado para la operación en planta"],
       ["El histórico es el más costoso", "28,7 ms de p95", "Sigue muy por debajo del umbral de 1,5 s"],
       ["Las lecturas se estancan con la concurrencia", "≈ 80 req/s desde 5 clientes", "El servidor corre con un solo proceso"],
       ["SQLite no escala en escrituras", "8,1 reg/s con 1, 5 y 10 clientes", "Un solo candado de archivo serializa todo"],
       ["PostgreSQL sí escala", "8 → 51 reg/s al pasar a 10 clientes", "Justifica el motor elegido en el ES2"],
       ["La visión es CPU pura", "2,3 s por ráfaga de 16 imágenes", "Estable; no depende de la base"],
       ["La red hacia us-east-1 pesa", "≈ 140 ms por petición", "Recomendación: región más cercana"]],
      anchos=[5.4, 4.6, 6.2], fuente=8.5)

nota("SQLite sostiene la demostración local; PostgreSQL es el motor que soporta varios operadores "
     "escribiendo a la vez. La medición convierte esa afirmación del diseño en evidencia.", "Lo esencial")

# =============================================================== 2 ===========
doc.add_heading("2. Metodología", level=1)

doc.add_heading("2.1 Entornos medidos", level=2)
titulo_tabla("Entornos de la prueba")
tabla(["Elemento", "Equipo local", "Nube (AWS)"],
      [["Servidor", "Windows 10, 12 núcleos, 32 GB RAM", "EC2 t3.micro, Ubuntu 24.04"],
       ["Base de datos", "SQLite (archivo)", "PostgreSQL 16 (contenedor)"],
       ["Almacenamiento", "Carpeta local", "Amazon S3"],
       ["Procesos de la app", "1 (uvicorn)", "1 (uvicorn en contenedor)"],
       ["Latencia de red", "≈ 0 ms (misma máquina)", "≈ 140 ms (Santiago → us-east-1)"]],
      anchos=[3.8, 6.4, 6.0], fuente=8.5)

doc.add_heading("2.2 Herramienta", level=2)
p("Se usó un generador propio (pruebas_carga/estres.py) en lugar de una herramienta externa, por "
  "tres razones: no requiere instalar nada en el servidor, permite mezclar peticiones autenticadas "
  "con distintos roles y deja los resultados crudos en JSON para analizarlos después.", align="j")
vinetas([
    ("Medición: ", "cada petición se cronometra con perf_counter y se clasifica como éxito o error según el código HTTP."),
    ("Estadística: ", "se calculan media, p50, p95, p99 y máximo, además de peticiones por segundo."),
    ("Recursos: ", "un hilo muestrea CPU y memoria del proceso del servidor cada 0,5 s."),
])

doc.add_heading("2.3 Escenarios ejecutados", level=2)
titulo_tabla("Diseño de los escenarios")
tabla(["#", "Escenario", "Qué mide", "Carga aplicada"],
      [["1", "Latencia secuencial", "Tiempo de respuesta por endpoint sin competencia",
        "60 peticiones a 4 endpoints"],
       ["2", "Lecturas concurrentes", "Cómo cambia el rendimiento al sumar clientes",
        "1, 5, 10 y 20 clientes · 12 s por nivel"],
       ["3", "Escrituras concurrentes", "Cuánto aguanta el registro simultáneo de inspecciones",
        "40 registros por nivel · 1, 5 y 10 clientes"],
       ["4", "Análisis de visión", "Costo de una ráfaga completa de 16 imágenes", "3 ráfagas seguidas"]],
      anchos=[0.9, 4.0, 6.0, 5.3], fuente=8.5)

doc.add_heading("2.4 Cómo reproducirla", level=2)
codigo("""# 1) levantar el servidor
cd App-Funcional
..\\APP-AZA\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000

# 2) correr la prueba (por defecto contra 127.0.0.1:8000)
python pruebas_carga\\estres.py

# 3) contra otro servidor (por ejemplo la nube)
set AZA_BASE=http://IP:8000
set AZA_SUFIJO=_nube
python pruebas_carga\\estres.py

# 4) gráficos y evidencias
python pruebas_carga\\graficos.py
python pruebas_carga\\comparacion.py""", "Comandos")

# =============================================================== 3 ===========
doc.add_heading("3. Resultados del equipo local (SQLite)", level=1)

doc.add_heading("3.1 Latencia por endpoint", level=2)
lat = LOCAL["escenarios"]["latencia"]
filas = [[nombre, r["peticiones"], n(r["media_ms"]), n(r["p95_ms"]), n(r["p99_ms"]), n(r["max_ms"]), r["errores"]]
         for nombre, r in lat.items()]
titulo_tabla("Latencia secuencial por endpoint (ms)")
tabla(["Endpoint", "Peticiones", "Media", "p95", "p99", "Máx", "Errores"], filas,
      anchos=[4.4, 2.2, 2.2, 2.0, 2.0, 2.0, 2.0], fuente=8.5, alinear_derecha=(1, 2, 3, 4, 5, 6))
nota("El histórico es el endpoint más costoso porque recorre y ordena la tabla completa; el "
     "dashboard y el detalle trabajan sobre un solo registro.", "Lectura")
figura("30_estres_latencia.png", "Latencia por endpoint: media, p95 y p99 sobre 60 peticiones.")

doc.add_heading("3.2 Lecturas concurrentes", level=2)
con = LOCAL["escenarios"]["concurrencia"]
titulo_tabla("Lecturas concurrentes por nivel de clientes")
tabla(["Clientes", "Peticiones", "req/s", "Media ms", "p95 ms", "p99 ms", "Errores"],
      [[c["nivel"], c["peticiones"], n(c["rps"]), n(c["media_ms"]), n(c["p95_ms"]),
        n(c["p99_ms"]), f"{c['tasa_error_pct']} %"] for c in con],
      anchos=[2.0, 2.4, 2.2, 2.4, 2.2, 2.2, 2.2], fuente=8.5, alinear_derecha=(0, 1, 2, 3, 4, 5, 6))
p("El rendimiento se estanca alrededor de 80 peticiones por segundo mientras la latencia crece de "
  "22 a 642 ms. Agregar clientes no aumenta el trabajo hecho, solo la cola de espera: el servidor "
  "tiene un único proceso y no aprovecha los doce núcleos del equipo.", align="j")
figura("31_estres_concurrencia.png", "Rendimiento y latencia frente al número de clientes.")

doc.add_heading("3.3 Escrituras concurrentes", level=2)
esc = LOCAL["escenarios"]["escrituras"]
titulo_tabla("Escrituras concurrentes sobre SQLite")
tabla(["Clientes", "Registros", "reg/s", "Media ms", "p95 ms", "Errores"],
      [[e["nivel"], e["creadas"], n(e["rps"]), n(e["media_ms"]), n(e["p95_ms"]), f"{e['tasa_error_pct']} %"]
       for e in esc],
      anchos=[2.2, 2.4, 2.2, 2.6, 2.6, 2.2], fuente=8.5, alinear_derecha=(0, 1, 2, 3, 4, 5))
p("Es el hallazgo más importante de la prueba. SQLite mantiene el mismo rendimiento con uno, cinco "
  "o diez clientes (alrededor de 8 registros por segundo) porque serializa todas las escrituras en "
  "un único candado de archivo. Lo que crece es la espera: la latencia p95 pasa de 166 ms a 3.480 ms, "
  "veintiún veces más, sin un solo error visible. El sistema no falla: se degrada.", align="j")
nota("Sin errores y con latencia creciente es el peor escenario para un operador real: cree que el "
     "sistema funciona, pero cada registro tarda segundos.", "Por qué importa")
figura("32_estres_escrituras.png", "Latencia de escritura según clientes concurrentes (SQLite).")

doc.add_heading("3.4 Análisis de visión y consumo de recursos", level=2)
vis = LOCAL["escenarios"]["vision"]
titulo_tabla("Costo del análisis de una ráfaga")
tabla(["Ráfaga", "Duración ms", "Ángulo medido", "Frames"],
      [[i + 1, d["duracion_ms"], f"{d['angulo']}°", d["frames"]] for i, d in enumerate(vis["detalles"])]
      + [["Media", n(vis["media_ms"]), "—", "—"]],
      anchos=[3.0, 4.0, 4.0, 3.0], fuente=8.5, alinear_derecha=(1, 2, 3))
rec = LOCAL.get("recursos", {})
if rec:
    p(f"Durante toda la prueba el proceso del servidor consumió {n(rec['cpu_medio_pct'])} % de CPU en "
      f"promedio y {n(rec['cpu_max_pct'])} % en el pico, con una memoria de {n(rec['ram_media_mb'])} MB "
      f"de media y {n(rec['ram_max_mb'])} MB en el máximo. El pico de CPU coincide con las ráfagas de "
      f"visión, que usan varios núcleos durante el análisis de las dieciséis imágenes.", align="j")
    figura("33_estres_recursos.png", "CPU y memoria del servidor durante la prueba.")

# =============================================================== 4 ===========
doc.add_heading("4. Comparación con el despliegue en la nube", level=1)
p("La misma prueba se ejecutó contra el sistema desplegado en AWS, con PostgreSQL 16 y "
  "almacenamiento S3. El objetivo no era comparar servidores, sino comprobar si el motor de base "
  "de datos cambia el comportamiento bajo escrituras concurrentes.", align="j")

ll, ln = LOCAL["escenarios"]["latencia"], NUBE["escenarios"]["latencia"]
mapa_l = {e["nivel"]: e for e in LOCAL["escenarios"]["escrituras"]}
mapa_n = {e["nivel"]: e for e in NUBE["escenarios"]["escrituras"]}
titulo_tabla("Comparación local frente a nube")
tabla(["Métrica", "SQLite (local)", "PostgreSQL (AWS)"],
      [["Dashboard · p95", f"{n(ll['Dashboard']['p95_ms'])} ms", f"{n(ln['Dashboard']['p95_ms'])} ms"],
       ["Histórico (20 filas) · p95", f"{n(ll['Histórico (20 filas)']['p95_ms'])} ms",
        f"{n(ln['Histórico (20 filas)']['p95_ms'])} ms"],
       ["Lecturas · 20 clientes", f"{n(LOCAL['escenarios']['concurrencia'][-1]['rps'])} req/s",
        f"{n(NUBE['escenarios']['concurrencia'][-1]['rps'])} req/s"],
       ["Lecturas · 20 clientes · p95", f"{n(LOCAL['escenarios']['concurrencia'][-1]['p95_ms'])} ms",
        f"{n(NUBE['escenarios']['concurrencia'][-1]['p95_ms'])} ms"],
       ["Escrituras · 1 cliente", f"{n(mapa_l[1]['rps'])} reg/s", f"{n(mapa_n[1]['rps'])} reg/s"],
       ["Escrituras · 5 clientes", f"{n(mapa_l[5]['rps'])} reg/s", f"{n(mapa_n[5]['rps'])} reg/s"],
       ["Escrituras · 10 clientes", f"{n(mapa_l[10]['rps'])} reg/s", f"{n(mapa_n[10]['rps'])} reg/s"],
       ["Escrituras · 10 clientes · p95", f"{n(mapa_l[10]['p95_ms'])} ms", f"{n(mapa_n[10]['p95_ms'])} ms"],
       ["Ráfaga de visión", f"{n(LOCAL['escenarios']['vision']['media_ms'])} ms",
        f"{n(NUBE['escenarios']['vision']['media_ms'])} ms"],
       ["Tasa de error", "0 %", "0 %"]],
      anchos=[6.4, 4.8, 4.8], fuente=8.5, alinear_derecha=(1, 2))
p("Con un solo cliente ambos entornos rinden parecido, porque el trabajo es el mismo y la red pesa "
  "poco frente al tiempo de cómputo. La diferencia aparece al sumar clientes: con diez escrituras "
  "simultáneas SQLite sigue en 8 registros por segundo, mientras que PostgreSQL sube a 51 y mantiene "
  "la latencia en 307 ms en lugar de 3.480 ms.", align="j")
figura("37_estres_comparacion_escrituras.png",
       "Escrituras concurrentes: rendimiento (izquierda) y latencia p95 (derecha).")
figura("38_estres_comparacion_latencia.png",
       "Latencia por endpoint en ambos entornos: la nube suma el costo de la red.")

# =============================================================== 5 ===========
doc.add_heading("5. Análisis", level=1)
doc.add_heading("5.1 El cuello de botella es el proceso, no la base", level=2)
p("Las lecturas se estancan en torno a 80 peticiones por segundo aunque se agreguen clientes, y la "
  "latencia crece de forma lineal con la concurrencia. Ese patrón corresponde a un servidor con un "
  "único proceso: las peticiones hacen cola y el trabajo se ejecuta de a una. No es un límite de "
  "PostgreSQL ni de SQLite, sino de la configuración de despliegue. La acción es ejecutar uvicorn "
  "con varios workers, uno por núcleo disponible.", align="j")

doc.add_heading("5.2 Las escrituras son el límite real", level=2)
p("Con SQLite, el rendimiento de escritura es plano mientras la latencia se multiplica por "
  "veintiuno. La causa es estructural: SQLite bloquea el archivo completo en cada escritura, de modo "
  "que el paralelismo no existe. PostgreSQL, en cambio, permite varias transacciones simultáneas y "
  "por eso su rendimiento sube con los clientes. Para un sistema de trazabilidad —donde cada "
  "inspección es una escritura— esta diferencia decide el motor.", align="j")

doc.add_heading("5.3 El costo de la distancia", level=2)
p("En la nube, incluso el endpoint de salud tarda cerca de 200 ms, que corresponde al viaje de ida y "
  "vuelta entre Santiago y us-east-1. No es lentitud de la aplicación: es latencia de red. Desplegar "
  "en una región más cercana (por ejemplo São Paulo) reduciría ese costo a la mitad o menos sin "
  "cambiar una línea de código.", align="j")

# =============================================================== 6 ===========
doc.add_heading("6. Conclusiones y recomendaciones", level=1)
vinetas([
    ("El sistema cumple el objetivo operativo. ", "Una ráfaga completa tarda 2,3 segundos, el tablero responde en 8,6 ms y no hubo errores en ninguna corrida."),
    ("El límite aparece con varios operadores. ", "Ahí la base de datos decide: PostgreSQL escala en escrituras y SQLite no."),
    ("La decisión del ES2 queda respaldada. ", "El motor relacional elegido no fue una preferencia: es el que sostiene la concurrencia medida."),
    ("Dos mejoras de configuración. ", "Varios workers en uvicorn y una región más cercana; ninguna requiere cambiar el código."),
    ("La prueba es repetible. ", "Los scripts y los resultados crudos quedan en el repositorio como línea base para comparar versiones futuras."),
])

titulo_tabla("Acciones derivadas de la prueba")
tabla(["Acción", "Motivo", "Tipo"],
      [["Ejecutar uvicorn con varios workers", "El rendimiento se estanca con un solo proceso", "Configuración"],
       ["Desplegar en una región más cercana", "140 ms de red por petición", "Configuración"],
       ["Mantener PostgreSQL en producción", "SQLite no escala en escrituras concurrentes", "Arquitectura"],
       ["Repetir la prueba con 50 clientes", "El objetivo del ES2 pedía 50 usuarios", "Validación"],
       ["Medir con volumen alto de datos", "Los índices recién agregados no se notan con decenas de filas", "Validación"]],
      anchos=[5.6, 7.0, 3.6], fuente=8.5)

# =============================================================== 7 ===========
doc.add_heading("7. Limitaciones de la prueba", level=1)
vinetas([
    "La carga se genera desde una sola máquina: el generador compite por CPU y red con el servidor cuando ambos están en el mismo equipo.",
    "El conjunto de datos es pequeño (decenas de filas), por lo que los índices y los planes de consulta no muestran su efecto real.",
    "La prueba mide la API, no la interfaz: no incluye el tiempo de renderizado del navegador.",
    "No se probó con la cámara real ni con operadores humanos; el escenario de visión usa imágenes sintéticas.",
    "El entorno de AWS es un laboratorio académico con recursos acotados, no un servidor de producción.",
])
nota("Estas limitaciones no invalidan la comparación entre motores, porque ambas corridas usaron el "
     "mismo generador y el mismo volumen de datos.", "Alcance")

# =============================================================== ANEXO A ====
salto()
doc.add_heading("Anexo A. Generador de carga (extracto)", level=1)
p("El generador completo está en App-Funcional/pruebas_carga/estres.py. Este es el núcleo de "
  "medición y de cálculo de percentiles:", align="j")
codigo("""def medir(self, metodo, ruta, **kw):
    t0 = time.perf_counter()
    try:
        r = self.http.request(metodo, ruta, headers=self.cab, **kw)
        ok = 200 <= r.status_code < 300
        cuerpo = r.json() if ok and "application/json" in r.headers.get("content-type", "") else None
    except Exception as exc:
        return (time.perf_counter() - t0) * 1000, False, {"error": str(exc)[:80]}
    return (time.perf_counter() - t0) * 1000, ok, cuerpo


def pct(datos, q):
    datos = sorted(datos)
    k = (len(datos) - 1) * q
    bajo, alto = int(k), min(int(k) + 1, len(datos) - 1)
    return datos[bajo] + (datos[alto] - datos[bajo]) * (k - bajo)


def resumen(latencias, errores, segundos):
    return {
        "peticiones": len(latencias),
        "errores": errores,
        "rps": round(len(latencias) / segundos, 2),
        "media_ms": round(statistics.mean(latencias), 2),
        "p50_ms": round(pct(latencias, 0.50), 2),
        "p95_ms": round(pct(latencias, 0.95), 2),
        "p99_ms": round(pct(latencias, 0.99), 2),
        "max_ms": round(max(latencias), 2),
    }""", "estres.py · medición y estadística")

codigo("""def escenario_concurrencia(cli, niveles=(1, 5, 10, 20), segundos=12):
    for nivel in niveles:
        lat, err = [], 0
        fin = time.time() + segundos

        def worker(_i):
            while time.time() < fin:
                for ruta in rutas:
                    ms, ok, _ = cli.medir("GET", ruta)
                    lat.append(ms)
                    if not ok:
                        err += 1

        with ThreadPoolExecutor(max_workers=nivel) as pool:
            list(pool.map(worker, range(nivel)))
        # se registra el resumen del nivel""", "estres.py · patrón de concurrencia")

# =============================================================== ANEXO B ====
doc.add_heading("Anexo B. Resultados crudos", level=1)
p("Resumen tal como queda en pruebas_carga/resultados.json y resultados_nube.json:", align="j")
lineas = ["escenario            clientes   local                nube"]
for c_l, c_n in zip(LOCAL["escenarios"]["concurrencia"], NUBE["escenarios"]["concurrencia"]):
    lineas.append(f"lecturas             {c_l['nivel']:>3}      {n(c_l['rps']):>6} req/s  p95 {n(c_l['p95_ms']):>7} ms     "
                  f"{n(c_n['rps']):>6} req/s  p95 {n(c_n['p95_ms']):>7} ms")
for e_l, e_n in zip(LOCAL["escenarios"]["escrituras"], NUBE["escenarios"]["escrituras"]):
    lineas.append(f"escrituras           {e_l['nivel']:>3}      {n(e_l['rps']):>6} reg/s  p95 {n(e_l['p95_ms']):>7} ms     "
                  f"{n(e_n['rps']):>6} reg/s  p95 {n(e_n['p95_ms']):>7} ms")
codigo("\n".join(lineas), "Consola")

p("")
p("Informe técnico del equipo · Noviembre de 2026", size=8.5, italic=True,
  color=RGBColor(0x78, 0x90, 0x9C), align="c")

doc.save(SALIDA)
print("guardado:", SALIDA)
print("tablas:", tablas[0], "| figuras:", figuras[0])
