# -*- coding: utf-8 -*-
"""Genera el documento «Arquitectura de datos y almacenamiento en la nube»."""
import os
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(RAIZ, "App-Funcional", "evidencias")
SALIDA = os.path.join(RAIZ, "documentos", "Arquitectura_de_Datos_AZA.docx")

VERDE = RGBColor(0x15, 0x4A, 0x1C)
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


def tabla(encabezados, filas, anchos=None, fuente=9):
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
        _sombrear(celda, "154A1C")
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            par = celdas[i].paragraphs[0]
            run = par.add_run(str(valor))
            run.font.size = Pt(fuente)
            par.paragraph_format.space_before = Pt(2)
            par.paragraph_format.space_after = Pt(2)
            if n % 2 == 1:
                _sombrear(celdas[i], GRIS_TABLA)
    if anchos:
        for fila in t.rows:
            for i, ancho in enumerate(anchos):
                fila.cells[i].width = Cm(ancho)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def _no_partir(t):
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))


def codigo(texto, titulo=None):
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
    run.font.size = Pt(8.5)
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


def figura(nombre, leyenda, ancho=15.4):
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


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


pie_pag = sec.footer.paragraphs[0]
pie_pag.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = pie_pag.add_run("Arquitectura de datos · AZA Analyzer · Aceros AZA ")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(0x78, 0x90, 0x9C)
campo = OxmlElement("w:fldSimple")
campo.set(qn("w:instr"), "PAGE")
pie_pag._p.append(campo)

# ============================================================== PORTADA =====
p("PROYECTO INTEGRADO · INACAP SANTIAGO CENTRO", size=9, bold=True,
  color=RGBColor(0x60, 0x7D, 0x8B), antes=60, despues=2)
p("Arquitectura de datos", size=27, bold=True, color=VERDE, antes=8, despues=0)
p("y almacenamiento en la nube", size=27, bold=True, color=VERDE, despues=10)
p("Por qué existe cada base de datos, qué guarda y dónde vive", size=13,
  color=RGBColor(0x33, 0x4A, 0x3A), despues=26)

tabla(["Dato", "Detalle"],
      [["Proyecto", "Sistema Web de Monitoreo y Trazabilidad del Trefilado"],
       ["Cliente", "Aceros AZA · Robotic Systems Chile"],
       ["Equipo", "Leonardo Daza (PO) · José Sarabia (SM) · Daniel Paredes (QA)"],
       ["Entorno", "EC2 t3.micro · Docker · PostgreSQL 16 · Amazon S3"],
       ["Versión", "1.0 — 21 de noviembre de 2026"]],
      anchos=[4.0, 12.2], fuente=9.5)

nota("Este documento responde cuatro preguntas: por qué hay dos almacenes, qué guarda "
     "cada uno, por qué se eligió Amazon S3 en lugar de MinIO, y cómo se comprueba que "
     "no queda nada guardado en un computador local.", "Objetivo")

salto()

# ============================================================== 1 ============
doc.add_heading("1. Resumen: qué hay y dónde está", level=1)
p("El sistema guarda dos tipos de información muy distintos, y por eso usa dos "
  "almacenes. No es una duplicación: cada uno resuelve un problema que el otro no "
  "resuelve bien.", align="j")
tabla(["Pieza", "Dónde vive", "Qué contiene"],
      [["Base relacional", "PostgreSQL 16 (contenedor en la instancia EC2)",
        "Usuarios, roles, sesiones, materiales, recetas, lotes, batches, inspecciones, alarmas y bitácora"],
       ["Almacén de objetos", "Amazon S3 (bucket aza-capturas-166178700885)",
        "Las 16 imágenes de cada ráfaga, las métricas del análisis y la imagen del diagnóstico"],
       ["Aplicación", "Contenedor Docker en la instancia EC2", "Código, interfaz y motor de análisis (sin datos)"],
       ["Visor de base", "Contenedor pgweb", "Ninguno: solo consulta la base"]],
      anchos=[3.4, 5.6, 7.2], fuente=8.5)

nota("Ningún dato del cliente queda en el computador del equipo. El PC solo conserva "
     "el código fuente (repositorio) y las capturas de evidencia.", "Lo esencial")

# ============================================================== 2 ============
doc.add_heading("2. Por qué dos almacenes y no uno solo", level=1)
p("La decisión se toma con cuatro criterios. Si se mira la naturaleza del dato, la "
  "respuesta aparece sola.", align="j")
tabla(["Criterio", "Los registros", "Las imágenes"],
      [["Forma del dato", "Filas y columnas con tipos fijos", "Archivos binarios (BMP y PNG)"],
       ["Tamaño", "Kilobytes por fila", "≈ 15 MB por ráfaga"],
       ["Cómo se consulta", "Por filtros, uniones y agregaciones (SQL)", "Por identificador exacto (clave del objeto)"],
       ["Volumen esperado", "Crece lento y ordenado", "Crece rápido: 16 archivos por inspección"],
       ["Qué se necesita", "Integridad, transacciones, relaciones", "Durabilidad y bajo costo por gigabyte"]],
      anchos=[3.6, 6.4, 6.4], fuente=8.5)

p("Guardar las imágenes como filas en PostgreSQL funcionaría, pero sería un mal uso: "
  "inflaría la base, encarecería los respaldos y volvería lenta cada consulta del "
  "tablero. Guardar los registros como archivos también funcionaría, pero se perderían "
  "las transacciones y las consultas por filtro que el negocio necesita.", align="j")

p("De ahí la separación clásica: una base relacional para lo estructurado y un almacén "
  "de objetos para lo no estructurado. La base guarda la clave del objeto; el objeto "
  "vive aparte.", align="j")

# ============================================================== 3 ============
doc.add_heading("3. PostgreSQL: la base de los registros", level=1)
p("PostgreSQL es la base principal y guarda todo lo que el negocio necesita consultar: "
  "quiénes son los usuarios, qué recetas existen, qué lote se está produciendo y qué "
  "ángulo se midió en cada inspección.", align="j")

doc.add_heading("3.1 Qué guarda", level=2)
tabla(["Tabla", "Para qué"],
      [["usuarios · roles · sesiones", "Quién entra, con qué perfil y con qué sesión activa"],
       ["materiales", "Familias y tipos del trazado (acero, cobre, latón, aluminio)"],
       ["recetas", "Tolerancia mínima y máxima, espesor y material de cada producto"],
       ["lotes · batches", "La estructura productiva: cada lote se divide en batches numerados"],
       ["inspecciones", "Cada medición con su ángulo, límites aplicados, estado y clave del objeto en S3"],
       ["alarmas", "Avisos automáticos cuando una pieza sale fuera de tolerancia"],
       ["auditoria", "Bitácora de quién hizo qué, cuándo y con qué valores"]],
      anchos=[4.6, 11.8], fuente=8.5)

doc.add_heading("3.2 Por qué una base relacional y no un archivo o un documento", level=2)
vinetas([
    ("Integridad referencial. ", "Una inspección no puede apuntar a una receta que no existe: la base lo impide."),
    ("Transacciones (ACID). ", "Si falla un paso al registrar una inspección y su alarma, no queda a medias."),
    ("Consultas por filtro. ", "«Cuántas piezas rechazó el lote L-2026-0410 en el turno B» es una consulta de una línea."),
    ("Datos semiestructurados con JSONB. ", "La bitácora guarda valores distintos según la entidad; JSONB permite ese contenido variable sin crear una tabla por cada tipo de evento."),
    ("Índices y rendimiento. ", "Los filtros por fecha, lote o estado se resuelven con índices, no recorriendo todo."),
])

doc.add_heading("3.3 El caso JSONB (y por qué importa)", level=2)
p("La tabla auditoria tiene una columna llamada «detalle» que no puede ser un texto "
  "fijo: un alta de usuario guarda rol y estado, mientras que una inspección guarda "
  "ángulo, lote, batch y la ruta del objeto. Ese contenido variable se guarda como "
  "JSONB, que en PostgreSQL es un tipo binario indexable y consultable.", align="j")
codigo("""{
  "modo": "dentro",
  "frames": 16,
  "duracion_ms": 1529,
  "velocidad_m_min": 12.0,
  "despues": {
    "lote": "L-2026-0410",
    "batch": 1,
    "angulo": 66.3,
    "estado": "aprobado",
    "receta": "A-36",
    "material": "Acero SAE 1010",
    "objeto": "lotes/L-2026-0410/B1/Trigger_0006_20261121_214659/resultado_analisis.png"
  }
}""", "Contenido real de auditoria.detalle (tipo jsonb)")
p("Y se puede consultar por dentro del JSON, que es la ventaja frente a un texto plano:", align="j")
codigo("""SELECT id, accion, detalle->'despues'->>'estado' AS estado,
       detalle->'despues'->>'lote'    AS lote
FROM auditoria
WHERE entidad = 'inspecciones'
ORDER BY id DESC;""", "Consultar el JSON como si fueran columnas")

# ============================================================== 4 ============
doc.add_heading("4. El almacén de objetos: las imágenes", level=1)
p("Cada inspección genera una ráfaga de 16 imágenes BMP de 640 × 480 (≈ 921 KB cada "
  "una), más un archivo de métricas y la imagen del diagnóstico. Son unos 15 MB por "
  "inspección. Ese material no se consulta por filtros: se accede por su identificador.", align="j")

doc.add_heading("4.1 Estructura de las claves", level=2)
p("La ruta se organiza por lote y batch para que la trazabilidad se vea también en el "
  "almacenamiento:", align="j")
codigo("""aza-capturas-166178700885/
  lotes/
    L-2026-0410/
      B1/
        Trigger_0006_20261121_214659/
          img_001.bmp ... img_016.bmp
          metricas.json
          resultado_analisis.png
      B2/
        ...
    L-2026-0411/
      B1/ ...""", "Organización del bucket")
p("El campo «imagen_clave» de la tabla inspecciones apunta exactamente a esa ruta. Si "
  "se conoce la clave, se obtiene el archivo; si se conoce la inspección, se obtiene la "
  "clave. No hace falta recorrer el bucket.", align="j")

doc.add_heading("4.2 Ciclo de vida de una ráfaga", level=2)
vinetas([
    ("1. Generación: ", "las 16 imágenes se crean en una carpeta temporal dentro del contenedor."),
    ("2. Análisis: ", "el motor de visión mide el ángulo sobre esas imágenes."),
    ("3. Subida: ", "la carpeta completa se sube a S3 bajo la ruta del lote y el batch."),
    ("4. Borrado local: ", "inmediatamente después se elimina la copia temporal. La única copia permanente queda en S3."),
    ("5. Registro: ", "la base guarda la clave del objeto, no el archivo."),
])

nota("Comprobado en el servidor: tras varias inspecciones, la carpeta de trabajo del "
     "contenedor queda con 0 archivos. Todo el contenido vive en el bucket.", "Verificación")

# ============================================================== 5 ============
doc.add_heading("5. Por qué Amazon S3 y no MinIO", level=1)
p("El informe ES2 propuso MinIO por una razón válida: es un servidor de objetos "
  "compatible con S3, de código abierto, que se puede instalar junto a la aplicación "
  "sin pagar almacenamiento. Era la opción correcta en el papel y así se documentó.", align="j")
p("Al momento de desplegar, MinIO ya no era posible. Estos son los hechos comprobados:", align="j")
tabla(["Comprobación", "Resultado"],
      [["Imagen minio/minio en Docker Hub", "404: el repositorio ya no existe"],
       ["Imágenes alternativas (Quay, GHCR, Bitnami)", "No disponibles"],
       ["Binarios comunitarios en dl.min.io", "410 Gone: descargas retiradas"],
       ["Binario disponible en su lugar", "MinIO AIStor, que exige licencia comercial y rechaza las operaciones S3 sin ella"]],
      anchos=[6.6, 9.8], fuente=8.5)
p("MinIO pasó a un modelo comercial. Frente a eso había tres caminos: comprar una "
  "licencia, usar un servidor S3 alternativo menos conocido, o usar el S3 nativo de "
  "AWS. Se eligió el tercero por tres motivos:", align="j")
vinetas([
    ("Es el mismo protocolo. ", "La aplicación habla la API de S3; MinIO solo la imitaba. El código no cambió ni una línea al pasar de uno a otro."),
    ("Es más confiable para la entrega. ", "Servicio administrado, con replicación y respaldos que no dependen de un contenedor que puede caerse."),
    ("Se puede volver a MinIO sin tocar código. ", "Basta definir la variable AZA_S3_ENDPOINT con la dirección de un MinIO propio; el resto es idéntico."),
])

nota("Para la defensa conviene decirlo así: «el diseño pedía almacenamiento de objetos "
     "compatible con S3; el proveedor MinIO dejó de distribuir su versión comunitaria, "
     "y como el protocolo es el mismo, se usó el servicio nativo de AWS sin modificar "
     "la aplicación».", "Cómo argumentarlo")

figura("26_nube_s3.png", "Objetos reales guardados en el bucket, con la ruta por lote y batch.")

# ============================================================== 6 ============
doc.add_heading("6. Por qué no se usó MongoDB (ni otra base NoSQL)", level=1)
p("El informe ES2 evaluó alternativas de motor y descartó MySQL por su menor soporte "
  "de JSONB e índices parciales. Frente a una base de documentos como MongoDB, el "
  "argumento es similar:", align="j")
tabla(["Necesidad del negocio", "Con PostgreSQL", "Con una base de documentos"],
      [["Relaciones entre receta, lote, batch e inspección", "Claves foráneas y uniones", "Se resuelven a mano o duplicando datos"],
       ["Transacciones al registrar inspección y alarma", "ACID nativo", "Posible, pero con más cuidado"],
       ["Contenido variable de la bitácora", "JSONB indexable", "Es su punto fuerte"],
       ["Una sola base que respaldar y una sola cadena de conexión", "Sí", "Habría que mantener dos motores"]],
      anchos=[5.4, 5.4, 5.6], fuente=8.5)
p("En resumen: el único caso que pedía flexibilidad de esquema era la bitácora, y "
  "JSONB lo cubre dentro de la misma base. Agregar un segundo motor no aportaba nada y "
  "sumaba operación.", align="j")

# ============================================================== 7 ============
doc.add_heading("7. Redis y Celery: lo que está declarado y aún no construido", level=1)
p("El informe declara Redis con Celery para trabajo asíncrono. Su función prevista es "
  "sacar del camino crítico las tareas que no necesitan respuesta inmediata: enviar el "
  "correo de una alarma, recalcular indicadores o reprocesar una ráfaga.", align="j")
p("Hoy el flujo es síncrono y funciona: una inspección tarda entre 1,5 y 6 segundos y "
  "el operador espera el resultado en pantalla. Por eso Redis no se implementó, y así "
  "se declara en la documentación y en la presentación. Es lo primero a agregar si se "
  "suma el envío de correos.", align="j")
nota("Declararlo abiertamente es mejor que fingir que existe: el profesor ya advirtió "
     "sobre lo «declarado pero no evidenciado».", "Transparencia")

# ============================================================== 8 ============
doc.add_heading("8. Todo en la nube, nada en local", level=1)
p("Esta es la parte que más suele confundirse. El sistema no necesita que ningún "
  "computador del equipo esté encendido: la aplicación, la base y los archivos viven "
  "en AWS.", align="j")
tabla(["Componente", "Dónde se ejecuta", "Dónde quedan los datos"],
      [["Aplicación e interfaz", "Contenedor en la instancia EC2 (AWS)", "No guarda datos: los escribe en la base y en S3"],
       ["Base de datos", "Contenedor PostgreSQL en la instancia EC2", "Volumen Docker dentro del servidor (en AWS)"],
       ["Imágenes de ráfaga", "Se generan en el contenedor", "Se suben a S3 y la copia local se elimina"],
       ["Visor de base", "Contenedor pgweb", "No guarda nada"],
       ["Computador del equipo", "Solo el navegador", "Solo el código fuente y las capturas de evidencia"]],
      anchos=[3.8, 5.6, 6.8], fuente=8.5)

doc.add_heading("8.1 Política de borrado", level=2)
p("La aplicación elimina la carpeta de trabajo apenas termina de subir la ráfaga, y la "
  "carpeta de calentamiento del motor de visión se borra al iniciar. La única copia "
  "permanente de las imágenes está en el bucket. Esto tiene una ventaja adicional de "
  "seguridad: si alguien accede al servidor, no encuentra un historial de fotos en el "
  "disco, solo la base y el bucket protegido.", align="j")

doc.add_heading("8.2 Cómo se comprueba", level=2)
codigo("""# en el servidor: la carpeta de trabajo debe quedar vacía
docker exec aza-app sh -c 'find /app/data/capturas -type f | wc -l'
# resultado esperado: 0

# los objetos están en el bucket
aws s3 ls --recursive s3://aza-capturas-166178700885/lotes/ | head""", "Verificación en dos pasos")

figura("24_nube_pgweb.png", "Los registros, disponibles desde el navegador sin depender de ningún equipo local.")

# ============================================================== 9 ============
doc.add_heading("9. Seguridad del almacenamiento", level=1)
tabla(["Riesgo", "Medida aplicada"],
      [["Acceso anónimo a las imágenes", "El bucket es privado: solo se lee con credenciales válidas de la cuenta"],
       ["Claves escritas en el código", "La aplicación usa el rol de la instancia de AWS; no hay claves en el código ni en el repositorio"],
       ["Copia de imágenes en el servidor", "Se eliminan después de subirlas; el disco no conserva el historial"],
       ["Acceso a la base de datos", "PostgreSQL no está expuesto a internet; se llega por túnel SSH desde una IP autorizada"],
       ["Consultas sin control", "El visor pgweb exige usuario y contraseña"],
       ["Alteración del historial", "La tabla de auditoría registra cada alta y cambio con sus valores anteriores y nuevos"]],
      anchos=[6.0, 10.4], fuente=8.5)

# ============================================================== 10 ===========
doc.add_heading("10. Costo del almacenamiento", level=1)
p("Los precios son referenciales de la región us-east-1 y deben confirmarse en la "
  "calculadora de AWS antes de contratar.", align="j")
tabla(["Concepto", "Cantidad estimada", "Costo mensual aproximado"],
      [["Instancia EC2 t3.micro", "1 instancia encendida", "USD 8 – 9 (o 0 con la capa gratuita)"],
       ["Almacenamiento S3 estándar", "5 GB de imágenes", "USD 0,12"],
       ["Solicitudes a S3", "Unas 10 000 al mes", "USD 0,05"],
       ["Transferencia de salida", "Menos de 100 GB", "USD 0 (incluida)"],
       ["PostgreSQL en la misma instancia", "Sin costo adicional", "USD 0"]],
      anchos=[5.6, 5.0, 5.8], fuente=8.5)
nota("En el laboratorio de AWS Academy todo esto se paga con los créditos del curso, "
     "por lo que no genera un cobro real mientras dure la asignatura.", "Contexto")

# ============================================================== 11 ===========
doc.add_heading("11. Resumen de decisiones", level=1)
tabla(["Decisión", "Elección", "Motivo en una línea"],
      [["Base de registros", "PostgreSQL 16", "Relaciones, transacciones y JSONB en un solo motor"],
       ["Contenido variable", "Columna JSONB", "La bitácora guarda valores distintos por entidad"],
       ["Almacenamiento de imágenes", "Amazon S3", "15 MB por ráfaga, acceso por clave, costo por gigabyte"],
       ["MinIO", "Descartado", "Dejó de distribuirse en su versión libre"],
       ["MongoDB u otra NoSQL", "Descartado", "JSONB cubre el único caso que lo justificaba"],
       ["Redis + Celery", "Pendiente", "El flujo actual es síncrono y no lo necesita"],
       ["Datos en el equipo local", "Ninguno", "Todo vive en AWS; el PC solo tiene el código"]],
      anchos=[4.4, 3.6, 8.4], fuente=8.5)

p("")
p("Documento técnico del equipo · Noviembre de 2026", size=8.5, italic=True,
  color=RGBColor(0x78, 0x90, 0x9C), align="c")

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
doc.save(SALIDA)
print("guardado:", SALIDA)
print("figuras:", figuras[0])
