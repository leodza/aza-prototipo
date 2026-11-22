# -*- coding: utf-8 -*-
"""Genera el Manual de Uso del prototipo AZA Analyzer (DOCX)."""
import os
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(RAIZ, "App-Funcional", "evidencias")
SALIDA = os.path.join(RAIZ, "documentos", "Manual_de_Uso_AZA.docx")

VERDE = RGBColor(0x15, 0x4A, 0x1C)
VERDE_CLARO = "E3EFE5"
GRIS_CODIGO = "F2F4F3"
GRIS_TABLA = "EDF1F2"
TINTA = RGBColor(0x1C, 0x24, 0x27)

doc = Document()

# ---------------------------------------------------------------- página ----
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
rpr = normal.element.get_or_add_rPr()
rfonts = rpr.find(qn("w:rFonts"))
if rfonts is None:
    rfonts = OxmlElement("w:rFonts")
    rpr.append(rfonts)
rfonts.set(qn("w:eastAsia"), "Calibri")


def _estilo(nombre, tam, color, antes, despues, negrita=True):
    st = doc.styles[nombre]
    st.font.name = "Calibri"
    st.font.size = Pt(tam)
    st.font.bold = negrita
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(antes)
    st.paragraph_format.space_after = Pt(despues)
    st.paragraph_format.keep_with_next = True
    return st


_estilo("Heading 1", 15, VERDE, 16, 7)
_estilo("Heading 2", 12, RGBColor(0x1F, 0x3A, 0x28), 12, 5)
_estilo("Heading 3", 11, RGBColor(0x33, 0x4A, 0x3A), 9, 4)


def p(texto="", style=None, size=None, bold=False, italic=False, align=None,
      antes=None, despues=None, color=None):
    par = doc.add_paragraph(style=style)
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
    elif align == "r":
        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if antes is not None:
        par.paragraph_format.space_before = Pt(antes)
    if despues is not None:
        par.paragraph_format.space_after = Pt(despues)
    return par


def vinetas(items, style="List Bullet"):
    for it in items:
        par = doc.add_paragraph(style=style)
        par.paragraph_format.space_after = Pt(2)
        if isinstance(it, tuple):
            run = par.add_run(it[0])
            run.bold = True
            par.add_run(it[1])
        else:
            par.add_run(it)


def _sombrear(celda, color):
    tcpr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def _borde_tabla(tabla, color="C9D4CE"):
    tbl = tabla._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def tabla(encabezados, filas, anchos=None, fuente=9, cabecera="154A1C"):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borde_tabla(t)
    hdr = t.rows[0].cells
    for i, texto in enumerate(encabezados):
        hdr[i].text = ""
        par = hdr[i].paragraphs[0]
        run = par.add_run(texto)
        run.bold = True
        run.font.size = Pt(fuente)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        par.paragraph_format.space_after = Pt(2)
        par.paragraph_format.space_before = Pt(2)
        _sombrear(hdr[i], cabecera)
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            par = celdas[i].paragraphs[0]
            run = par.add_run(str(valor))
            run.font.size = Pt(fuente)
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.space_before = Pt(2)
            if n % 2 == 1:
                _sombrear(celdas[i], GRIS_TABLA)
    if anchos:
        for fila in t.rows:
            for i, ancho in enumerate(anchos):
                fila.cells[i].width = Cm(ancho)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def _no_partir(tabla):
    """Evita que la tabla se corte entre dos páginas."""
    tr = tabla.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)


def codigo(texto, titulo=None):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_partir(t)
    celda = t.rows[0].cells[0]
    celda.text = ""
    _sombrear(celda, GRIS_CODIGO)
    _borde_tabla(t, "D8E0DB")
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
    run.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


figuras = [0]


def figura(nombre, leyenda, ancho=15.6):
    ruta = os.path.join(EVID, nombre)
    if not os.path.exists(ruta):
        return
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(6)
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


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------- pie de pág. --
pie = sec.footer.paragraphs[0]
pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = pie.add_run("Manual de Uso · AZA Analyzer · Aceros AZA ")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(0x78, 0x90, 0x9C)
campo = OxmlElement("w:fldSimple")
campo.set(qn("w:instr"), "PAGE")
pie._p.append(campo)

# =============================================================== PORTADA ====
p("PROYECTO INTEGRADO · INACAP SANTIAGO CENTRO", size=9, bold=True,
  color=RGBColor(0x60, 0x7D, 0x8B), antes=60, despues=2)
p("Sistema Web de Monitoreo y", size=26, bold=True, color=VERDE, despues=0, antes=8)
p("Trazabilidad del Trefilado", size=26, bold=True, color=VERDE, despues=10)
p("Manual de uso y guía de la base de datos", size=13, color=RGBColor(0x33, 0x4A, 0x3A), despues=26)

tabla(["Dato", "Detalle"],
      [["Cliente", "Aceros AZA · Robotic Systems Chile"],
       ["Producto", "AZA Analyzer — prototipo funcional (ES3)"],
       ["Equipo", "Leonardo Daza (Product Owner)\nJosé Sarabia (Scrum Master · backend)\nDaniel Paredes (frontend · QA)"],
       ["Docente", "Armin Vladimir Brun Rüth"],
       ["Entorno publicado", "http://13.223.49.56:8000 (aplicación)\nhttp://13.223.49.56:8081 (base de datos)"],
       ["Repositorio", "https://github.com/leodza/aza-prototipo"],
       ["Versión del manual", "1.0 — 21 de noviembre de 2026"]],
      anchos=[4.6, 11.6], fuente=9.5)

nota("Este manual explica qué hace el sistema, dónde queda guardada la información, "
     "cómo consultarla y qué medidas de seguridad tiene implementadas.", "Para qué sirve")

salto()

# =============================================================== CONTENIDO ===
doc.add_heading("Contenido", level=1)
for titulo in [
    "1. Qué es el sistema y cómo se usa",
    "2. Cómo está montado (arquitectura)",
    "3. Dónde está almacenada la información",
    "4. Guía de uso de la aplicación",
    "5. Cómo hacer consultas a la base de datos",
    "6. Recorrido completo de una inspección",
    "7. Seguridad implementada",
    "8. Evidencias y enlaces",
    "9. Problemas frecuentes",
]:
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(3)
    run = par.add_run(titulo)
    run.font.size = Pt(11)

salto()

# =============================================================== 1 ===========
doc.add_heading("1. Qué es el sistema y cómo se usa", level=1)
p("AZA Analyzer mide el ángulo de salida del trefilado a partir de una ráfaga de imágenes, "
  "compara ese ángulo con la tolerancia de la receta que se está produciendo y decide si la "
  "pieza se aprueba o se rechaza. Cada medición queda registrada y asociada a su receta, su "
  "lote, su batch y su material, que es lo que permite reconstruir la trazabilidad después.",
  align="j")
p("La aplicación se usa desde el navegador, sin instalar nada. El operador entra con su usuario "
  "y un PIN, dispara una inspección y ve el resultado en pantalla; el supervisor consulta el "
  "histórico y la bitácora; el administrador gestiona recetas, materiales y usuarios.", align="j")

doc.add_heading("1.1 Tipos de usuario", level=2)
tabla(["Rol", "Usuario de prueba", "Qué puede hacer"],
      [["Operador", "ldaza (PIN 1234)", "Ver el turno en curso, disparar inspecciones, consultar recetas"],
       ["Supervisor", "jsarabia (PIN 1234)", "Todo lo del operador más el histórico completo y la auditoría"],
       ["Administrador", "dparedes (PIN 1234)", "Todo, incluidos usuarios, recetas y catálogo de materiales"],
       ["Integrador", "servicio / servicio", "Solo registrar inspecciones por API (sin acceso a la interfaz)"]],
      anchos=[3.0, 4.2, 9.0], fuente=9)

doc.add_heading("1.2 Direcciones del sistema publicado", level=2)
tabla(["Qué", "Dirección", "Credenciales"],
      [["Aplicación web", "http://13.223.49.56:8000", "ldaza / jsarabia / dparedes · PIN 1234"],
       ["Base de datos (visor web)", "http://13.223.49.56:8081", "usuario aza · clave AzaLab2026Db"],
       ["Repositorio del código", "github.com/leodza/aza-prototipo", "público, sin credenciales"]],
      anchos=[4.4, 6.6, 5.2], fuente=9)

nota("El entorno corre en un laboratorio de AWS Academy. Cuando la sesión del laboratorio "
     "termina, la instancia se detiene y la dirección deja de responder; para volver a "
     "levantarlo están los tres comandos de la sección 8.", "Importante")

# =============================================================== 2 ===========
def diagrama(lineas, ancho=64):
    """Dibuja una caja ASCII perfectamente alineada (solo caracteres ASCII)."""
    borde = "+" + "-" * (ancho - 2) + "+"
    cuerpo = [borde]
    for linea in lineas:
        cuerpo.append("| " + linea.ljust(ancho - 4)[:ancho - 4] + " |")
    cuerpo.append(borde)
    return "\n".join(cuerpo)


doc.add_heading("2. Cómo está montado (arquitectura)", level=1)
p("Todo el sistema corre en una sola máquina virtual (una instancia EC2 t3.micro con Ubuntu 24.04), "
  "dentro de contenedores Docker. Hay tres piezas principales más un visor de base de datos:", align="j")

codigo(diagrama([
    "Tu navegador",
    "    |",
    "    |  HTTP :8000",
    "    v",
    "Servidor en AWS (EC2 t3.micro, Ubuntu 24.04)",
    "",
    "[ app ]  FastAPI + interfaz web",
    "   |                    |",
    "   | SQLAlchemy         | boto3 (protocolo S3)",
    "   v                    v",
    "[ db ] PostgreSQL 16     Amazon S3",
    "10 tablas                bucket aza-capturas-...",
    "(datos)                  (imagenes de las rafagas)",
    "",
    "[ pgweb ] visor web de PostgreSQL  :8081",
]))

doc.add_heading("2.1 Componentes", level=2)
tabla(["Componente", "Tecnología", "Para qué sirve"],
      [["app", "Python 3.12 · FastAPI · SQLAlchemy", "Expone la API REST y sirve la interfaz; ejecuta el análisis de las imágenes"],
       ["db", "PostgreSQL 16", "Guarda usuarios, materiales, recetas, lotes, batches, inspecciones y auditoría"],
       ["pgweb", "pgweb (visor web)", "Permite ver las tablas y ejecutar SQL desde el navegador"],
       ["S3", "Amazon S3", "Guarda las imágenes de cada ráfaga y el diagnóstico generado"],
       ["Docker Compose", "docker compose", "Levanta y mantiene los contenedores arriba"]],
      anchos=[2.9, 5.2, 8.1], fuente=9)

p("La aplicación no guarda imágenes dentro de la base de datos: guarda solo la ruta del archivo "
  "(la clave del objeto). Así la base se mantiene liviana y las imágenes se pueden consultar por "
  "separado. Es la separación clásica entre datos estructurados (tablas) y no estructurados (archivos).",
  align="j")

# =============================================================== 3 ===========
doc.add_heading("3. Dónde está almacenada la información", level=1)
p("La información está repartida en dos lugares, y conviene entender bien cuál es cuál antes de "
  "buscar algo.", align="j")

doc.add_heading("3.1 Base de datos PostgreSQL (datos estructurados)", level=2)
p("Esquema público de la base «aza», con diez tablas. Estos son los datos que hay hoy:", align="j")
tabla(["Tabla", "Qué guarda", "Filas actuales"],
      [["usuarios", "Cuentas del personal: usuario, nombre, PIN cifrado, rol, estado y bloqueo", "5"],
       ["roles", "Los cuatro perfiles del sistema (operador, supervisor, administrador, integrador)", "4"],
       ["sesiones", "Sesiones activas y tokens de refresco (permite revocar el acceso)", "—"],
       ["materiales", "Catálogo de familias y tipos: acero SAE 1010, inoxidable 304, cobre, latón, aluminio", "7"],
       ["recetas", "Recetas de producción: tolerancia mínima y máxima, espesor y material", "6"],
       ["lotes", "Lotes de producción, con su receta y turno", "6"],
       ["batches", "Subdivisiones del lote, numeradas de 1 a 3", "18"],
       ["inspecciones", "Cada medición: ángulo, límites aplicados, estado, material, velocidad y clave del objeto en S3", "50"],
       ["alarmas", "Avisos generados cuando una pieza sale fuera de tolerancia", "0"],
       ["auditoria", "Bitácora con detalle JSONB: quién, qué y los valores anteriores y nuevos", "16"]],
      anchos=[2.6, 10.3, 3.3], fuente=8.5)

p("La tabla más importante es «inspecciones». Cada fila es una medición y contiene, además del "
  "ángulo, una copia de los límites con los que fue juzgada: por eso, si mañana se cambia una "
  "receta, el histórico no se altera.", align="j")

doc.add_heading("3.2 Almacenamiento de objetos (las imágenes)", level=2)
p("En el bucket «aza-capturas-166178700885» se guarda una carpeta por ráfaga, con esta estructura:",
  align="j")
codigo("""lotes/
  L-2026-0410/
    B1/
      Trigger_0006_20261121_214659/
        img_001.bmp ... img_016.bmp    16 imágenes de la ráfaga (640 x 480)
        metricas.json                  mediciones del pipeline
        resultado_analisis.png         imagen con el círculo y el ángulo detectados
    B2/ ...
  L-2026-0411/
    B1/ ...""")
p("Cada ráfaga ocupa alrededor de 15 MB (921 KB por imagen BMP). En total, hoy hay 54 objetos "
  "guardados. El campo «imagen_clave» de la tabla inspecciones apunta exactamente a esa ruta.", align="j")

nota("Cuando se abre el detalle de una inspección en la aplicación, la imagen que se muestra se "
     "descarga desde S3 usando esa clave, no desde el disco del servidor.", "Dato útil")

# =============================================================== 4 ===========
doc.add_heading("4. Guía de uso de la aplicación", level=1)

doc.add_heading("4.1 Entrar", level=2)
vinetas([
    "Abrir http://13.223.49.56:8000 en el navegador.",
    "Elegir el usuario (por ejemplo jsarabia) y escribir el PIN 1234.",
    "Al entrar siempre se llega al panel principal (Dashboard).",
])
figura("01_login.png", "Pantalla de acceso. El menú que aparece después depende del rol.")

doc.add_heading("4.2 El panel principal", level=2)
p("Muestra cuántas inspecciones hay en el turno, cuántas se aprobaron y cuántas se rechazaron, "
  "la última medición con su aguja de ángulo, la tendencia de las últimas veinte y la lista de "
  "registros recientes con su receta, lote y batch.", align="j")
figura("21_nube_dashboard.png", "Dashboard con datos reales del sistema desplegado en AWS.")

doc.add_heading("4.3 Disparar una inspección", level=2)
vinetas([
    ("Receta: ", "se elige la receta que se está produciendo; define la tolerancia."),
    ("Condición: ", "«Normal» (la velocidad afecta el ángulo), «Aleatorio» (puede salir bien o mal) o «Forzar rechazo»."),
    ("Velocidad del tren: ", "de 4 a 30 m/min. La nominal es 12; cada m/min agrega o quita unos 2,8°."),
    ("Simular ráfaga: ", "genera 16 imágenes, las analiza con el pipeline de visión y registra el resultado."),
])
figura("23_nube_simulador.png", "Simulador. Abajo a la derecha aparece el ángulo medido y su estado.")

p("Si la pieza sale rechazada, la aplicación indica si conviene subir o bajar la velocidad para "
  "volver al rango. Esa es la corrección que se hace en planta.", align="j")

doc.add_heading("4.4 Consultar el histórico", level=2)
p("La pantalla de Histórico permite filtrar por fecha, receta, lote y estado, y ordenar por "
  "«Lote → batch» o por «Más recientes». Cada fila muestra el identificador de la receta (#1) y "
  "del batch (#1) junto al nombre, y el botón Exportar CSV descarga lo filtrado.", align="j")
figura("22_nube_historico.png", "Histórico ordenado por lote y batch, con identificadores visibles.")

doc.add_heading("4.5 Ver el detalle de una inspección", level=2)
p("Al hacer clic en cualquier fila se abre el detalle: la imagen del diagnóstico, los datos de la "
  "medición (ángulo, límites, estado), la trazabilidad técnica (frame de salida, centro y radio "
  "del círculo, duración, motor de visión) y la bitácora de esa inspección.", align="j")

doc.add_heading("4.6 Recetas, materiales y usuarios", level=2)
vinetas([
    ("Recetas: ", "listado con su tolerancia, espesor y material. Solo el administrador puede crear."),
    ("Catálogo de materiales: ", "familias y tipos disponibles (acero, cobre, latón, aluminio). Cada receta se asocia a uno."),
    ("Usuarios: ", "el administrador crea cuentas, las activa o desactiva y las da de baja (baja lógica: el historial se conserva)."),
    ("Auditoría: ", "bitácora general de accesos y cambios."),
])
figura("06b_materiales.png", "Catálogo de materiales y recetas asociadas (vista de administrador).")

# =============================================================== 5 ===========
doc.add_heading("5. Cómo hacer consultas a la base de datos", level=1)
p("Hay dos maneras: desde el navegador con el visor pgweb, o por terminal con psql. La primera no "
  "requiere instalar nada.", align="j")

doc.add_heading("5.1 Con el visor web (recomendado)", level=2)
vinetas([
    "Abrir http://13.223.49.56:8081",
    "Autenticarse con usuario aza y clave AzaLab2026Db.",
    "En la barra izquierda aparecen las diez tablas: al hacer clic en una se ven sus filas.",
    "Para escribir SQL, ir a la pestaña «Query», escribir la consulta y pulsar «Run Query».",
])
figura("24_nube_pgweb.png", "Visor pgweb: a la izquierda las tablas, arriba la pestaña Query.")

doc.add_heading("5.2 Consultas de ejemplo", level=2)
p("Sirven tal cual, copiando y pegando en la pestaña Query.", align="j")

codigo("""-- 1) Cuántos registros hay en cada tabla
SELECT 'usuarios' AS tabla, count(*) FROM usuarios
UNION ALL SELECT 'materiales', count(*) FROM materiales
UNION ALL SELECT 'recetas',    count(*) FROM recetas
UNION ALL SELECT 'lotes',      count(*) FROM lotes
UNION ALL SELECT 'batches',    count(*) FROM batches
UNION ALL SELECT 'inspecciones', count(*) FROM inspecciones
UNION ALL SELECT 'auditoria',  count(*) FROM auditoria;""", "Ver el tamaño de la base")

codigo("""-- 2) Las últimas inspecciones con toda su trazabilidad
SELECT i.id, i.fecha_hora, r.nombre AS receta, l.codigo AS lote,
       b.numero AS batch, i.material, i.angulo, i.estado, i.imagen_clave
FROM inspecciones i
LEFT JOIN recetas r ON r.id = i.receta_id
LEFT JOIN lotes   l ON l.id = i.lote_id
LEFT JOIN batches b ON b.id = i.batch_id
ORDER BY i.id DESC
LIMIT 10;""", "Consultar el histórico completo")

codigo("""-- 3) Porcentaje de aprobación por receta
SELECT r.nombre, count(*) AS total,
       count(*) FILTER (WHERE i.estado = 'aprobado') AS aprobadas,
       round(100.0 * count(*) FILTER (WHERE i.estado = 'aprobado') / count(*), 1) AS pct
FROM inspecciones i
JOIN recetas r ON r.id = i.receta_id
GROUP BY r.nombre
ORDER BY total DESC;""", "Indicador de calidad")

codigo("""-- 4) Qué se hizo y quién lo hizo
SELECT fecha, accion, entidad, entidad_id, detalle
FROM auditoria
ORDER BY id DESC
LIMIT 10;""", "Bitácora de auditoría")

codigo("""-- 5) Insertar una inspección de prueba
INSERT INTO inspecciones (fecha_hora, receta_id, lote_id, batch_id, angulo,
                          limite_min, limite_max, estado, origen, material)
VALUES (now(), 1, 1, 1, 72.5, 45, 90, 'aprobado', 'prueba_manual', 'Acero SAE 1010')
RETURNING id, angulo, estado;

-- 6) Borrarla después de la prueba
DELETE FROM inspecciones WHERE origen = 'prueba_manual';""", "Escribir datos a mano")

nota("Son datos reales: un DELETE o un DROP se ejecutan de inmediato. Para experimentar sin riesgo, "
     "escribir BEGIN; antes de la prueba y ROLLBACK; al final; los cambios se descartan.", "Precaución")

doc.add_heading("5.3 Por terminal (psql)", level=2)
p("El servidor de base de datos no está expuesto a internet: se llega por un túnel SSH cifrado. "
  "Hay que abrir el túnel en una ventana y dejar esa ventana abierta.", align="j")
codigo(""":: 1) abrir el túnel (dejar esta ventana abierta)
ssh -i "App-Funcional\\deploy\\aza-llave.pem" -N -L 5432:127.0.0.1:5432 ubuntu@13.223.49.56

:: 2) en otra ventana, entrar a la base
set PGPASSWORD=AzaLab2026Pg
psql -h 127.0.0.1 -U aza -d aza""", "Windows · PowerShell o CMD")
codigo("""\\dt                  -- listar tablas
\\d inspecciones      -- ver la estructura de una tabla
\\x                   -- vista vertical (útil con filas anchas)
SELECT count(*) FROM inspecciones;
\\q                   -- salir""", "Comandos útiles dentro de psql")

# =============================================================== 6 ===========
doc.add_heading("6. Recorrido completo de una inspección", level=1)
p("Este es el camino que sigue una medición desde que se dispara hasta que queda almacenada. "
  "Sirve para entender qué parte del sistema hace cada cosa.", align="j")
pasos = [
    ("1. Se dispara desde la interfaz. ", "El navegador llama a POST /api/simular con la receta, la velocidad y la condición."),
    ("2. Se valida el acceso. ", "El servidor verifica el token JWT y que el rol tenga permiso para esa operación."),
    ("3. Se genera la ráfaga. ", "Se crean 16 imágenes BMP: 6 de fondo y 10 con la pieza y su arco de salida."),
    ("4. Se analiza con visión. ", "El pipeline busca el frame de salida, detecta el círculo de la pieza y mide el ángulo. Tarda entre 1,5 y 6 segundos."),
    ("5. Se evalúa. ", "El ángulo se compara con el mínimo y el máximo de la receta: aprobado, rechazado o sin medición. Si no cumple, se crea una alarma."),
    ("6. Se guardan las imágenes. ", "La ráfaga y el diagnóstico se suben a S3 y queda la clave del objeto."),
    ("7. Se registra en la base. ", "Se inserta la fila en inspecciones con receta, lote, batch, material, velocidad, desviación y clave del objeto, y se anota el evento en auditoría."),
    ("8. Se muestra. ", "El dashboard y el histórico se actualizan con el nuevo registro."),
]
for titulo, texto in pasos:
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.left_indent = Cm(0.4)
    run = par.add_run(titulo)
    run.bold = True
    run.font.color.rgb = VERDE
    par.add_run(texto)

# =============================================================== 7 ===========
doc.add_heading("7. Seguridad implementada", level=1)
p("La seguridad del prototipo se apoya en cuatro capas: cómo se autentica el usuario, qué puede "
  "hacer cada rol, cómo se protegen las credenciales y cómo se aísla la infraestructura.", align="j")

doc.add_heading("7.1 Autenticación", level=2)
tabla(["Mecanismo", "Implementación", "Para qué"],
      [["Cifrado del PIN", "PBKDF2-HMAC-SHA256 con 200.000 iteraciones y sal única por usuario", "El PIN nunca se guarda en claro; aunque se copie la base no se puede leer"],
       ["Token de acceso", "JWT firmado con HS256, vigencia de 15 minutos", "Identifica la sesión en cada petición sin consultar la base"],
       ["Token de refresco", "Cadena aleatoria guardada como hash SHA-256, vigencia de 8 horas, rotación y revocación", "Permite renovar la sesión sin volver a escribir el PIN, y cerrarla a distancia"],
       ["Bloqueo por intentos", "5 intentos fallidos bloquean la cuenta 15 minutos", "Frena los ataques de fuerza bruta contra el PIN"],
       ["Cierre de sesión", "El token de refresco se revoca y la sesión se marca como cerrada", "Una sesión cerrada no se puede reutilizar"]],
      anchos=[3.3, 7.3, 5.6], fuente=8.5)

doc.add_heading("7.2 Autorización por rol (RBAC)", level=2)
p("El menú se arma según el rol, pero lo importante es que el servidor vuelve a comprobar el "
  "permiso en cada endpoint: si alguien intenta llamar a una ruta que no le corresponde, recibe "
  "un error 403 aunque conozca la dirección.", align="j")
tabla(["Operación", "Operador", "Supervisor", "Administrador", "Integrador"],
      [["Ver dashboard, histórico y detalle", "Sí", "Sí", "Sí", "No"],
       ["Disparar inspecciones", "Sí", "Sí", "Sí", "No"],
       ["Registrar inspección por API", "No", "No", "No", "Sí"],
       ["Ver auditoría y estado del almacenamiento", "No", "Sí", "Sí", "No"],
       ["Crear recetas y materiales", "No", "No", "Sí", "No"],
       ["Gestionar usuarios", "No", "No", "Sí", "No"]],
      anchos=[6.4, 2.4, 2.4, 2.8, 2.4], fuente=8.5)

doc.add_heading("7.3 Protección de credenciales y secretos", level=2)
vinetas([
    ("Contraseñas de infraestructura en variables de entorno. ", "Las claves de PostgreSQL, de S3 y la firma de los JWT viven en un archivo .env que no se versiona."),
    ("El repositorio no contiene secretos. ", "El .gitignore excluye *.pem, .env y los datos generados; la llave SSH y las claves de la base nunca se subieron a GitHub."),
    ("Acceso al repositorio acotado. ", "Se usa una «deploy key» con permiso de escritura únicamente sobre ese repositorio, no una llave de la cuenta completa."),
    ("Principio de menor privilegio en la nube. ", "La instancia usa el rol del laboratorio y solo se abren los puertos necesarios."),
])

doc.add_heading("7.4 Seguridad de red", level=2)
tabla(["Puerto", "Servicio", "Acceso permitido", "Comentario"],
      [["22", "SSH", "Solo la IP del equipo del proyecto", "Administración del servidor"],
       ["8000", "Aplicación web", "Cualquier origen", "Necesario para la demostración"],
       ["8081", "Visor de base de datos", "Cualquier origen, con usuario y clave", "Protegido con autenticación básica"],
       ["5432", "PostgreSQL", "Cerrado a internet", "Solo accesible desde dentro del servidor o por túnel SSH"],
       ["9000", "API de almacenamiento", "Cerrado", "Ya no se usa (se migró a S3)"]],
      anchos=[1.9, 4.0, 5.4, 4.9], fuente=8.5)

doc.add_heading("7.5 Auditoría", level=2)
p("Cada inicio de sesión, creación, cambio o baja queda registrado en la tabla auditoria con la "
  "fecha, el usuario, la acción, la entidad afectada y un detalle. El detalle de una inspección "
  "muestra además su propia bitácora, filtrada solo a los eventos de ese registro.", align="j")

doc.add_heading("7.6 Riesgos conocidos y qué falta", level=2)
tabla(["Riesgo", "Estado actual", "Recomendación"],
      [["Sin HTTPS", "El sitio viaja por HTTP; la clave de acceso podría interceptarse en una red no confiable", "Instalar un proxy con certificado (Caddy o Nginx + Let's Encrypt) antes de usarlo fuera del laboratorio"],
       ["PIN de demostración 1234", "Todas las cuentas de prueba comparten el mismo PIN", "Cambiarlos antes de la entrega o desactivar las cuentas que no se usen"],
       ["Base de datos de demostración", "Los datos se borran al reiniciarse el laboratorio", "Para uso real, migrar a RDS con respaldos automáticos"],
       ["Sin envío de correos", "La alarma se registra, pero no se notifica por correo", "Integrar un servicio de correo en la etapa siguiente"]],
      anchos=[3.6, 6.4, 6.2], fuente=8.5)

# =============================================================== 8 ===========
doc.add_heading("8. Evidencias y enlaces", level=1)
tabla(["Recurso", "Dónde"],
      [["Aplicación en vivo", "http://13.223.49.56:8000"],
       ["Visor de la base de datos", "http://13.223.49.56:8081"],
       ["Repositorio con el código y los commits", "https://github.com/leodza/aza-prototipo"],
       ["Capturas del sistema (24 imágenes)", "App-Funcional/evidencias/"],
       ["Consultas reales a PostgreSQL", "evidencias/25_nube_postgresql.png"],
       ["Objetos guardados en S3", "evidencias/26_nube_s3.png"],
       ["Historial de commits", "evidencias/27_git_commits.png"],
       ["Guía de despliegue en AWS", "App-Funcional/GUIA-AWS.md"]],
      anchos=[7.4, 8.8], fuente=9)

p("Para volver a levantar el sistema desde cero, en el servidor:", align="j")
codigo("""cd /opt/aza
docker compose up -d --build
docker compose ps""", "Tres comandos")

# =============================================================== 9 ===========
doc.add_heading("9. Problemas frecuentes", level=1)
tabla(["Síntoma", "Causa probable", "Solución"],
      [["La página no carga", "El laboratorio de AWS se detuvo", "Reiniciar el laboratorio y volver a levantar la instancia"],
       ["Error 401 al abrir el visor de la base", "Falta autenticarse o la clave cambió", "Usar usuario aza y clave AzaLab2026Db"],
       ["El login dice «cuenta bloqueada»", "Cinco intentos fallidos", "Esperar 15 minutos o pedir al administrador que desbloquee la cuenta"],
       ["Una inspección sale «sin medición»", "El arco cayó en una zona donde el algoritmo no detecta señal", "Volver a disparar; el simulador reintenta solo"],
       ["El histórico aparece vacío", "El filtro de fecha quedó en otro día", "Pulsar «Limpiar» y aplicar de nuevo"],
       ["Las imágenes no se ven en el detalle", "El objeto no está en el bucket", "Revisar la clave en la tabla inspecciones y el contenido de S3"]],
      anchos=[4.6, 5.6, 6.0], fuente=8.5)

p("")
p("Manual elaborado por el equipo del proyecto · Noviembre de 2026", size=8.5, italic=True,
  color=RGBColor(0x78, 0x90, 0x9C), align="c")

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
doc.save(SALIDA)
print("guardado:", SALIDA)
print("figuras:", figuras[0])
