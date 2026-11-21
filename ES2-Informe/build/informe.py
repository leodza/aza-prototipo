"""Genera el informe ES2 en DOCX a partir de los datos y los diagramas generados."""
import os
import sys
import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datos as D

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DIAG = os.path.join(BASE, "diagramas")
LOGO = os.path.join(BASE, "..", "APP-AZA", "assets", "logo.png")
SALIDA = os.path.join(BASE, "Informe_ES2_AZA.docx")

VERDE = RGBColor(0x1B, 0x5E, 0x20)
VERDE_CLARO = RGBColor(0x2E, 0x7D, 0x32)
GRIS = RGBColor(0x37, 0x47, 0x4F)
GRIS_CLARO = RGBColor(0x78, 0x90, 0x9C)
ROJO = RGBColor(0xC6, 0x28, 0x28)

HEX_VERDE_HDR = "1B5E20"
HEX_VERDE_SUAVE = "E8F5E9"
HEX_GRIS_SUAVE = "F1F4F5"
HEX_AMARILLO = "FFF8E1"

_n_fig = [0]
_n_tab = [0]
_n_pag = 0


# --------------------------------------------------------------------------- #
# utilidades XML
# --------------------------------------------------------------------------- #
def _sombreado(celda, hex_color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _borde_celda(celda, color="CFD8DC", size=4):
    tcPr = celda._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:color"), color)
        borders.append(el)
    tcPr.append(borders)


def _repetir_encabezado(fila):
    trPr = fila._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _no_partir_fila(fila):
    trPr = fila._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _campo(parrafo, instr, marcador="1"):
    run = parrafo.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = marcador
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(it)
    run._r.append(fld2)
    run._r.append(txt)
    run._r.append(fld3)


# --------------------------------------------------------------------------- #
# estilos y estructura
# --------------------------------------------------------------------------- #
def configurar_estilos(doc):
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    st.font.color.rgb = RGBColor(0x1C, 0x24, 0x27)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.12
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

    for nombre, tam, color, antes, despues in [
        ("Heading 1", 18, VERDE, 18, 8),
        ("Heading 2", 14, VERDE_CLARO, 14, 6),
        ("Heading 3", 12, GRIS, 10, 4),
    ]:
        s = doc.styles[nombre]
        s.font.name = "Calibri"
        s.font.size = Pt(tam)
        s.font.color.rgb = color
        s.font.bold = True
        s.paragraph_format.space_before = Pt(antes)
        s.paragraph_format.space_after = Pt(despues)
        s.paragraph_format.keep_with_next = True

    for nombre in ("List Bullet", "List Number"):
        s = doc.styles[nombre]
        s.font.name = "Calibri"
        s.font.size = Pt(10.5)
        s.paragraph_format.space_after = Pt(3)


def configurar_pagina(doc):
    for seccion in doc.sections:
        seccion.page_width = Cm(21)
        seccion.page_height = Cm(29.7)
        seccion.left_margin = Cm(2.2)
        seccion.right_margin = Cm(2.0)
        seccion.top_margin = Cm(2.2)
        seccion.bottom_margin = Cm(2.0)
        seccion.header_distance = Cm(1.1)
        seccion.footer_distance = Cm(1.0)


def agregar_encabezado_pie(doc):
    seccion = doc.sections[0]
    enc = seccion.header
    p = enc.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run("ES2 · Diseño de la solución — Aceros AZA / Robotic Systems Chile")
    r.font.size = Pt(8)
    r.font.color.rgb = GRIS_CLARO
    r.font.name = "Calibri"

    pie = seccion.footer
    p = pie.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Página ")
    r.font.size = Pt(8)
    r.font.color.rgb = GRIS_CLARO
    _campo(p, "PAGE")
    r2 = p.add_run(" de ")
    r2.font.size = Pt(8)
    r2.font.color.rgb = GRIS_CLARO
    _campo(p, "NUMPAGES")


def h1(doc, texto):
    return doc.add_heading(texto, level=1)


def h2(doc, texto):
    return doc.add_heading(texto, level=2)


def h3(doc, texto):
    return doc.add_heading(texto, level=3)


def p(doc, texto, negrita_inicial=None, cursiva=False, fs=None, color=None,
      alineacion=None, espacio_despues=None):
    par = doc.add_paragraph()
    if negrita_inicial:
        r = par.add_run(negrita_inicial)
        r.bold = True
        if fs:
            r.font.size = Pt(fs)
    r = par.add_run(texto)
    r.italic = cursiva
    if fs:
        r.font.size = Pt(fs)
    if color:
        r.font.color.rgb = color
    if alineacion is not None:
        par.alignment = alineacion
    if espacio_despues is not None:
        par.paragraph_format.space_after = Pt(espacio_despues)
    return par


def bullets(doc, items, estilo="List Bullet"):
    for it in items:
        par = doc.add_paragraph(style=estilo)
        if isinstance(it, tuple):
            r = par.add_run(it[0])
            r.bold = True
            par.add_run(it[1])
        else:
            par.add_run(it)


def criterio(doc, codigo, nivel, descripcion):
    """Recuadro que declara el criterio de la rúbrica y cómo se cumple."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    celda = t.cell(0, 0)
    celda.width = Cm(16.8)
    _sombreado(celda, HEX_VERDE_SUAVE)
    _borde_celda(celda, "2E7D32", 8)
    par = celda.paragraphs[0]
    r = par.add_run(f"Criterio {codigo}  ·  Nivel esperado: {nivel}")
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = VERDE
    par2 = celda.add_paragraph()
    r2 = par2.add_run(descripcion)
    r2.font.size = Pt(9)
    r2.italic = True
    r2.font.color.rgb = GRIS
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def evidencia(doc, texto):
    par = doc.add_paragraph()
    r = par.add_run("Evidencia en este documento: ")
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = VERDE
    r2 = par.add_run(texto)
    r2.font.size = Pt(9)
    r2.italic = True
    r2.font.color.rgb = GRIS
    par.paragraph_format.space_after = Pt(10)


def _fijar_anchos(tabla_obj, anchos):
    """Fuerza el reparto de anchos (tblLayout fixed) para que el visor no lo recalcule."""
    tbl = tabla_obj._tbl
    tblPr = tbl.tblPr
    for el in tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(el)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    for el in tblPr.findall(qn("w:tblW")):
        tblPr.remove(el)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(int(sum(anchos) * 567)))
    tblPr.append(tblW)
    for i, ancho in enumerate(anchos):
        if i < len(tabla_obj.columns):
            tabla_obj.columns[i].width = Cm(ancho)


def tabla(doc, encabezados, filas, anchos=None, fs=8.5, titulo=None,
          resaltar_col0=False, alinear_num=None):
    if titulo:
        _n_tab[0] += 1
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(8)
        cap.paragraph_format.space_after = Pt(3)
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run(f"Tabla {_n_tab[0]}. ")
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = VERDE
        r2 = cap.add_run(titulo)
        r2.bold = True
        r2.font.size = Pt(9)
        r2.font.color.rgb = GRIS

    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if anchos:
        _fijar_anchos(t, anchos)

    hdr = t.rows[0]
    _repetir_encabezado(hdr)
    for i, enc in enumerate(encabezados):
        celda = hdr.cells[i]
        celda.width = Cm(anchos[i]) if anchos else Cm(16.8 / len(encabezados))
        _sombreado(celda, HEX_VERDE_HDR)
        par = celda.paragraphs[0]
        par.paragraph_format.space_after = Pt(2)
        par.paragraph_format.space_before = Pt(2)
        r = par.add_run(enc)
        r.bold = True
        r.font.size = Pt(fs)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for idx, fila in enumerate(filas):
        celdas = t.add_row().cells
        _no_partir_fila(t.rows[-1])
        for i, valor in enumerate(fila):
            celda = celdas[i]
            celda.width = Cm(anchos[i]) if anchos else Cm(16.8 / len(encabezados))
            if idx % 2 == 1:
                _sombreado(celda, HEX_GRIS_SUAVE)
            par = celda.paragraphs[0]
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.space_before = Pt(2)
            r = par.add_run(str(valor))
            r.font.size = Pt(fs)
            if resaltar_col0 and i == 0:
                r.bold = True
            if alinear_num and i in alinear_num:
                par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figura(doc, archivo, ancho_cm, titulo, nota=None):
    ruta = os.path.join(DIR_DIAG, archivo)
    if not os.path.exists(ruta):
        p(doc, f"[Falta la figura {archivo}]", cursiva=True, color=ROJO)
        return
    _n_fig[0] += 1
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.keep_with_next = True
    par.add_run().add_picture(ruta, width=Cm(ancho_cm))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(2)
    r = cap.add_run(f"Figura {_n_fig[0]}. ")
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = VERDE
    r2 = cap.add_run(titulo)
    r2.font.size = Pt(9)
    r2.font.color.rgb = GRIS
    if nota:
        n = doc.add_paragraph()
        n.alignment = WD_ALIGN_PARAGRAPH.CENTER
        n.paragraph_format.space_after = Pt(10)
        rn = n.add_run(nota)
        rn.italic = True
        rn.font.size = Pt(8)
        rn.font.color.rgb = GRIS_CLARO


def salto_pagina(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# --------------------------------------------------------------------------- #
# portada y preliminares
# --------------------------------------------------------------------------- #
def portada(doc):
    for _ in range(2):
        doc.add_paragraph()

    if os.path.exists(LOGO):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run().add_picture(LOGO, height=Cm(2.6))

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run("ACEROS AZA  ·  ROBOTIC SYSTEMS CHILE")
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = GRIS_CLARO

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(24)
    r = par.add_run(D.PROYECTO)
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = VERDE

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run("ES2 — Diseño de la solución de software")
    r.font.size = Pt(15)
    r.font.color.rgb = VERDE_CLARO
    r.bold = True

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run("Planificación · Arquitectura 4+1 · Prototipado · Modelo de datos · "
                    "Seguridad · Plan de pruebas")
    r.font.size = Pt(10)
    r.italic = True
    r.font.color.rgb = GRIS

    for _ in range(3):
        doc.add_paragraph()

    t = doc.add_table(rows=5, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    filas = [
        ("Institución", D.INSTITUCION),
        ("Asignatura", D.ASIGNATURA),
        ("Docente", D.DOCENTE),
        ("Sección", D.SECCION),
        ("Fecha de entrega", D.FECHA),
    ]
    for i, (k, v) in enumerate(filas):
        c0, c1 = t.rows[i].cells
        c0.width = Cm(4.6)
        c1.width = Cm(9.0)
        r0 = c0.paragraphs[0].add_run(k)
        r0.bold = True
        r0.font.size = Pt(10)
        r0.font.color.rgb = GRIS
        r1 = c1.paragraphs[0].add_run(v)
        r1.font.size = Pt(10)

    for _ in range(2):
        doc.add_paragraph()

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run("Integrantes")
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = VERDE

    for nombre, rol, _ in D.EQUIPO:
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(1)
        r = par.add_run(nombre)
        r.bold = True
        r.font.size = Pt(10.5)
        r2 = par.add_run(f"  ·  {rol.split(' · ')[0]}")
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = GRIS_CLARO

    salto_pagina(doc)


def marco_referencia(doc):
    h1(doc, "Marco de referencia")
    p(doc, "Este apartado fija los conceptos y las fuentes sobre los que se apoyan las decisiones de "
           "diseño. Las citas siguen el formato APA 7 y todas las obras mencionadas aparecen en la "
           "lista de referencias al final del documento.")

    h3(doc, "Industria 4.0 y trazabilidad industrial")
    p(doc, "La Industria 4.0 describe la integración de sistemas ciberfísicos, sensores y plataformas "
           "digitales en los procesos productivos, con el objetivo de conectar el taller con los "
           "sistemas de información de la empresa (Kagermann et al., 2013; Lasi et al., 2014). En ese "
           "marco, el valor no está únicamente en medir: está en conservar el dato y poder "
           "explotarlo después (Schwab, 2017). Un sistema que mide pero no persiste deja el "
           "conocimiento en la pantalla del operador y lo pierde al terminar el turno.")
    p(doc, "Ese es exactamente el diagnóstico del ES1: el sistema de visión ya produce el ángulo, pero "
           "el resultado vive en la pantalla y no queda asociado a un lote, a una receta ni a un "
           "operador. La contribución de este diseño no es medir mejor, sino convertir una medición "
           "efímera en un registro trazable (Lasi et al., 2014).")

    h3(doc, "Dashboards y visualización de información")
    p(doc, "Un tablero operativo no es un reporte: su función es responder una pregunta en segundos "
           "mientras el proceso está ocurriendo (Few, 2006). Por eso el diseño de la interfaz parte de "
           "la tarea del usuario y del tipo de dato que necesita ver, y no de la disponibilidad de "
           "indicadores (Shneiderman, 1996). La jerarquía visual y la reducción de ruido importan más "
           "que la cantidad de gráficos (Knaflic, 2015), criterio que se aplicó al dashboard del "
           "operador: una cifra dominante, su estado y la tolerancia, nada más.")

    h3(doc, "Arquitecturas de servicios REST")
    p(doc, "REST es un estilo arquitectónico y no un protocolo: se define por un conjunto de "
           "restricciones, entre ellas la interfaz uniforme y la ausencia de estado en la sesión "
           "(Fielding, 2000). De ahí se desprenden dos decisiones del diseño: cada recurso se expone "
           "con una representación explícita y la identidad del cliente viaja en el token y no en el "
           "servidor. La documentación del contrato con OpenAPI es la práctica habitual para que un "
           "consumidor —en este caso el sistema de visión— integre sin ambigüedad (Richardson & Ruby, "
           "2007).")

    h3(doc, "Gestión de identidades y accesos (IAM)")
    p(doc, "El control de acceso basado en roles (RBAC) asigna permisos a roles y no a personas, lo "
           "que reduce el error operativo y hace auditable la autorización (Sandhu et al., 1996). Los "
           "lineamientos de identidad digital recomiendan credenciales de vigencia corta con rotación "
           "y verificación en el servidor (National Institute of Standards and Technology, 2020), y la "
           "referencia de riesgos de aplicaciones web insiste en que la autorización se valide en el "
           "backend y no en el cliente (OWASP Foundation, 2021). Ambas ideas sostienen la política de "
           "sesión y la matriz RBAC del capítulo 2.1.5.")

    h3(doc, "Metodologías de desarrollo")
    p(doc, "La elección de metodología debe responder al contexto del equipo y del problema, no a una "
           "preferencia previa (Sommerville, 2016; Pressman & Maxim, 2020). Scrum organiza el trabajo "
           "en iteraciones con un dueño de producto que prioriza el valor (Schwaber & Sutherland, "
           "2020); Kanban optimiza el flujo continuo limitando el trabajo en curso (Anderson, 2010); y "
           "las vistas 4+1 permiten documentar la arquitectura desde cinco perspectivas "
           "complementarias (Kruchten, 1995). El capítulo 2.1.1.1 evalúa estas alternativas con una "
           "matriz ponderada antes de seleccionar.")

    h3(doc, "Datos, calidad y seguridad del software")
    p(doc, "El diseño de una base relacional debe equilibrar la normalización con el rendimiento de "
           "lectura, y separar los datos estructurados del almacenamiento de objetos "
           "(Kleppmann, 2017). La separación de responsabilidades por capas es el patrón que permite "
           "que esa decisión no se propague por todo el sistema (Fowler, 2002). En calidad, las "
           "pruebas se diseñan desde el requisito y sus condiciones de borde, no desde la "
           "implementación (Myers et al., 2011), y la práctica de escribir la prueba antes del código "
           "reduce el retrabajo (Beck, 2002). En seguridad, el principio vigente es incorporar los "
           "controles durante el desarrollo y no al final del ciclo (McGraw, 2006), con la accesibilidad "
           "verificada contra criterios medibles (World Wide Web Consortium, 2018).")


def ficha_documento(doc):
    h1(doc, "Ficha del documento")
    p(doc, "Este informe corresponde a la evaluación ES2 del desafío y documenta el diseño de la "
           "solución de software previo a su construcción. Se estructura según los quince criterios "
           "de la rúbrica de la evaluación, en el mismo orden en que se evalúan, y cada sección "
           "declara explícitamente el criterio que cubre y la evidencia que lo respalda.")

    tabla(doc,
          ["Campo", "Detalle"],
          [("Proyecto", D.PROYECTO),
           ("Empresa", D.EMPRESA),
           ("Contraparte técnica", D.CONTRAPARTE),
           ("Documento", D.DOCUMENTO),
           ("Versión", D.VERSION),
           ("Fecha", D.FECHA),
           ("Equipo", ", ".join(n for n, _, _ in D.EQUIPO)),
           ("Metodología", "Scrum con vistas 4+1 de RUP"),
           ("Stack", "React + Tailwind · FastAPI · PostgreSQL · MinIO · Redis · Docker"),
           ("Criterios cubiertos", "2.1.1.1 a 2.1.6.15 (15 criterios, 100 puntos)"),
           ("Base del diagnóstico", "Informe ES1 del equipo: 10 necesidades (N1–N10), 14 historias "
                                    "de usuario, 12 RF y 12 RNF, conservados con la misma numeración "
                                    "(ver Anexo G)"),
           ("Anexos", "A casos de uso · B DDL · C trazabilidad · D preguntas de defensa · "
                      "E supuestos y glosario · F inventario de evidencias · G catálogo del ES1")],
          anchos=[4.2, 12.6], fs=9, titulo="Identificación del documento", resaltar_col0=True)

    tabla(doc,
          ["Integrante", "Rol en el proyecto", "Responsabilidad principal"],
          D.EQUIPO,
          anchos=[3.6, 5.4, 7.8], fs=9,
          titulo="Composición del equipo y roles", resaltar_col0=True)

    h3(doc, "Control de versiones")
    tabla(doc,
          ["Versión", "Fecha", "Autor", "Cambios"],
          [("0.1", "08-10-2026", "Leonardo Daza", "Estructura del informe y secciones 2.1.1"),
           ("0.2", "14-10-2026", "José Sarabia", "Arquitectura 4+1, datos y seguridad"),
           ("0.3", "19-10-2026", "Daniel Paredes", "Prototipo, guía visual y plan de pruebas"),
           ("1.0", "23-10-2026", "Equipo completo",
            "Revisión conjunta, normalización de tablas y entrega")],
          anchos=[1.8, 2.6, 3.8, 8.6], fs=9, titulo="Historial de versiones del documento")

    h3(doc, "Cómo leer este informe")
    bullets(doc, [
        ("Cada sección abre con un recuadro de criterio: ", "indica el código de la rúbrica y lo que "
         "se espera en el nivel más alto, para que la evaluación sea directa."),
        ("Tablas y figuras numeradas: ", "las referencias cruzadas permiten seguir una decisión desde "
         "la necesidad de negocio hasta la prueba que la verifica."),
        ("Anotaciones de trazabilidad: ", "cada requisito cita la historia de usuario de origen y el "
         "caso de uso que lo materializa (matriz completa en el Anexo C)."),
        ("Continuidad con el ES1: ", "los identificadores N, HU, RF y RNF son exactamente los del "
         "informe de diagnóstico del equipo; el catálogo completo se reproduce en el Anexo G."),
        ("Supuestos académicos: ", "los volúmenes y frecuencias que la empresa no entregó están "
         "declarados como supuestos en el Anexo E y marcados como tales en el texto."),
    ])

    h3(doc, "Índice")
    par = doc.add_paragraph()
    r = par.add_run("Si el índice aparece vacío, selecciónelo y presione F9 (o Actualizar tabla) para "
                    "generarlo a partir de los títulos del documento.")
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = GRIS_CLARO
    _campo(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u',
           "Índice automático — presione F9 (o clic derecho › Actualizar campo) para generarlo.")
    salto_pagina(doc)


# --------------------------------------------------------------------------- #
# 2.1.1
# --------------------------------------------------------------------------- #
def seccion_211(doc):
    h1(doc, "2.1.1  Gestión del proyecto")

    p(doc, "El equipo adoptó una metodología híbrida: Scrum como marco de gestión del trabajo y las "
           "vistas 4+1 de Kruchten (RUP) como marco de documentación de la arquitectura. La decisión "
           "responde a una condición concreta del proyecto: los requisitos de negocio son "
           "razonablemente estables —registrar, consultar y visualizar inspecciones—, pero el diseño "
           "de la solución debía validarse con usuarios antes de construir, y la rúbrica exige "
           "justificar la arquitectura con cinco puntos de vista. Scrum aporta la iteración; RUP, el "
           "rigor arquitectónico.")

    p(doc, "Trabajar con tres integrantes impone una restricción práctica: no es viable mantener "
           "ceremonias extensas ni una fase de documentación separada de la construcción. Por eso se "
           "adoptaron únicamente los artefactos de cada marco que agregan valor verificable: backlog y "
           "sprints de Scrum; vistas, casos de uso y modelo de datos de RUP.")

    # ---- 2.1.1.1 ----
    h2(doc, "2.1.1.1  Actividades y fases del proyecto")
    criterio(doc, "2.1.1.1", "Destacado (5 puntos)",
             "Actividades y fases definidas, alineadas con la metodología, detalladas con plazos "
             "alcanzables y responsables asignados.")
    evidencia(doc, "Tablas 4 a 6 y Figura 1 (cronograma con 29 actividades, 7 sprints, fechas y "
                   "responsable por actividad).")

    h3(doc, "Evaluación y selección de la metodología")
    p(doc, "La elección de la metodología no se tomó por preferencia del equipo: se evaluó primero y "
           "se seleccionó después. La literatura sobre ingeniería de software coincide en que el marco "
           "de trabajo debe responder al contexto del equipo y del problema, y no a una costumbre "
           "previa (Sommerville, 2016; Pressman & Maxim, 2020). Por eso se definieron seis criterios "
           "ponderados según su peso en este proyecto y se puntuó cada alternativa de 1 a 5.")

    p(doc, "Criterios y ponderación utilizada: ")
    bullets(doc, [
        ("Adaptabilidad al cambio (25 %): ", "capacidad de absorber ajustes de alcance sin rehacer el "
         "diseño."),
        ("Documentación arquitectónica exigida (20 %): ", "la rúbrica requiere justificar la "
         "arquitectura con cinco vistas (Kruchten, 1995)."),
        ("Ajuste a un equipo de tres personas (15 %): ", "ceremonias y artefactos sostenibles con ese "
         "tamaño."),
        ("Entregas frecuentes y validación temprana (15 %): ", "permite corregir el rumbo con usuarios "
         "antes de construir."),
        ("Trazabilidad requisito → prueba (15 %): ", "cada historia debe poder rastrearse hasta su "
         "evidencia de prueba (Myers et al., 2011)."),
        ("Curva de aprendizaje compatible con el plazo (10 %): ", "el semestre no admite un marco que "
         "el equipo deba aprender desde cero."),
    ])

    p(doc, "El promedio ponderado se calculó como la suma de cada puntaje multiplicado por su peso. El "
           "resultado se muestra en la última columna de la Tabla 4, junto con el motivo de descarte de "
           "cada alternativa; la matriz completa, criterio por criterio, está en el Anexo H.")
    tabla(doc,
          ["Metodología", "Punto de partida", "Cuándo conviene", "Puntaje", "Decisión en este proyecto"],
          D.METODOLOGIAS,
          anchos=[2.8, 3.4, 3.1, 1.5, 6.0], fs=8.2,
          titulo="Evaluación cuantitativa de metodologías, puntaje ponderado y decisión",
          resaltar_col0=True)

    p(doc, "La lectura del resultado es consistente con el marco teórico: Scrum obtuvo el mayor puntaje "
           "porque organiza el trabajo en iteraciones con un dueño de producto que prioriza el valor "
           "(Schwaber & Sutherland, 2020), y las vistas 4+1 aportaron el marco de documentación que la "
           "rúbrica exige (Kruchten, 1995). Kanban quedó segundo: optimiza el flujo continuo y limita "
           "el trabajo en curso (Anderson, 2010), pero no impone puntos de cierre formales, y este "
           "proyecto se evalúa en cuatro hitos con fechas fijas. Cascada obtuvo el puntaje más bajo "
           "porque fija la interfaz y los requisitos antes de validarlos, que es precisamente el error "
           "que el diagnóstico del ES1 buscaba evitar.")

    p(doc, "La combinación adoptada se concreta en tres acuerdos operativos: (1) cada criterio de la "
           "rúbrica se convierte en una o más actividades del backlog con su entregable; (2) la "
           "arquitectura se documenta una sola vez, en el Sprint 1, y se actualiza si cambia una "
           "decisión; (3) toda decisión técnica relevante se registra con su justificación, no solo "
           "con su descripción.")

    h3(doc, "Fases del proyecto (sprints)")
    p(doc, "El proyecto se organizó en siete sprints de dos a tres semanas entre el 10 de agosto y el "
           "14 de diciembre de 2026, con las cuatro fechas de evaluación fijadas por el descriptor de "
           "la asignatura: ES1 el 7 de septiembre, ES2 el 19 de octubre, ES3 el 23 de noviembre y ES4 "
           "el 14 de diciembre. Los tres primeros sprints producen el diseño que documenta este "
           "informe; los restantes corresponden a la construcción, el despliegue y el cierre.")
    tabla(doc,
          ["Fase", "Período", "Enfoque", "Actividades principales", "Entregable"],
          D.SPRINTS_TABLA,
          anchos=[1.7, 3.0, 2.2, 6.4, 3.5], fs=8.2,
          titulo="Fases del proyecto, objetivos y entregables", resaltar_col0=True)

    h3(doc, "Actividades, plazos y responsables")
    p(doc, "La Tabla 6 desglosa las 29 actividades del proyecto con su identificador, el sprint en que "
           "se ejecutan, las fechas de inicio y término, el responsable y el entregable verificable. "
           "Las fechas coinciden con las barras de la Figura 1.")
    filas_act = [(a[0], a[1], a[2], a[3], a[4], D.RESPONSABLES[a[5]], a[6]) for a in D.ACTIVIDADES]
    tabla(doc,
          ["ID", "Actividad", "Sprint", "Inicio", "Fin", "Responsable", "Entregable"],
          filas_act,
          anchos=[1.1, 5.0, 1.3, 1.4, 1.4, 2.6, 4.0], fs=7.6,
          titulo="Cronograma detallado de actividades con plazos y responsables", resaltar_col0=True)

    figura(doc, "01_cronograma_gantt.png", 16.4,
           "Cronograma del proyecto con las 29 actividades, los siete sprints y los cuatro hitos de "
           "evaluación",
           "Las bandas de color identifican el sprint; las iniciales al final de cada barra indican el "
           "responsable. Las líneas verticales punteadas marcan los hitos de evaluación: ES1 (07-sep), "
           "ES2 (19-oct), ES3 (23-nov) y ES4 (14-dic).")

    h3(doc, "Roles, ceremonias y definición de terminado")
    tabla(doc,
          ["Elemento", "Definición adoptada en este proyecto"],
          [("Product Owner", "Leonardo Daza. Único responsable de priorizar el backlog y de aceptar "
                             "los entregables; representa la voz de la contraparte."),
           ("Scrum Master", "José Sarabia. Facilita las ceremonias, elimina bloqueos y vela por que la "
                            "deuda técnica no se acumule sin registro."),
           ("Equipo de desarrollo", "Los tres integrantes. José Sarabia concentra backend y datos; "
                                    "Daniel Paredes, frontend y calidad; Leonardo Daza, análisis, UX y "
                                    "validación."),
           ("Sprint Planning", "Al inicio de cada sprint: se seleccionan historias del backlog "
                               "priorizado y se estiman con póker de planificación."),
           ("Daily asíncrono", "Reporte escrito diario en el canal del equipo (qué hice, qué sigue, qué "
                               "me bloquea). Reemplaza la reunión diaria por la disponibilidad horaria "
                               "dispareja del equipo."),
           ("Sprint Review", "Al cierre: demostración del incremento al PO y registro del feedback "
                             "recibido (Tabla 19)."),
           ("Retrospectiva", "Al cierre: una acción de mejora concreta por sprint, con responsable y "
                             "verificación en el sprint siguiente."),
           ("Definición de terminado", "Código revisado por un par, pruebas automatizadas en verde, "
                                       "documentación actualizada y criterio de aceptación verificado "
                                       "por el PO.")],
          anchos=[3.6, 13.2], fs=8.6,
          titulo="Roles de Scrum, ceremonias y definición de terminado", resaltar_col0=True)

    # ---- 2.1.1.2 ----
    h2(doc, "2.1.1.2  Dependencias y prioridades del cronograma")
    criterio(doc, "2.1.1.2", "Destacado (5 puntos)",
             "Todas las dependencias y prioridades correctamente identificadas, optimizando el flujo "
             "de trabajo.")
    evidencia(doc, "Tabla 8 (30 dependencias con tipo y holgura), Figura 2 (red y ruta crítica), "
                   "Tabla 9 (priorización MoSCoW) y Figura 3 (matriz valor/esfuerzo).")

    p(doc, "Las dependencias se clasificaron con la notación clásica de gestión de proyectos: FS "
           "(fin a inicio) cuando una actividad no puede comenzar hasta que la anterior termine, y SS "
           "(inicio a inicio) cuando ambas pueden avanzar en paralelo con un desfase. El segundo tipo "
           "se usó para las actividades que comparten insumos, por ejemplo cuando el modelo de datos "
           "puede iniciarse en paralelo con la arquitectura una vez fijado el alcance.")

    tabla(doc,
          ["Actividad", "Predecesora", "Tipo", "Holgura", "¿Ruta crítica?"],
          D.DEPENDENCIAS,
          anchos=[3.0, 3.0, 3.4, 2.6, 4.8], fs=8.4,
          titulo="Dependencias entre actividades, holgura y pertenencia a la ruta crítica",
          resaltar_col0=True)

    figura(doc, "02_red_dependencias.png", 16.4,
           "Red de dependencias del cronograma y ruta crítica del proyecto",
           "En rojo, la cadena de holgura cero: cualquier atraso en esas actividades desplaza la "
           "entrega de ES2 y de ES4. En azul, las actividades paralelizables (seguridad y prototipo v2), "
           "con la holgura expresada en días.")

    h3(doc, "Ruta crítica y su lectura")
    p(doc, "La ruta crítica arranca en la conformación del equipo y atraviesa el levantamiento de "
           "necesidades, el backlog, la arquitectura, el modelo de datos, el plan de pruebas y la "
           "redacción del informe. Esto confirma una intuición que conviene explicitar: en este "
           "proyecto el camino crítico no es el desarrollo, sino la cadena de diseño. Un día perdido "
           "en el levantamiento de requisitos se propaga hasta la entrega de ES2; en cambio, retrasar "
           "el análisis de amenazas tres días no afecta la fecha, porque su holgura es de tres días.")

    p(doc, "Sobre esa base se tomaron dos decisiones de secuenciación para proteger el plazo. La "
           "primera fue adelantar el prototipo navegable (A09) para que la validación con usuarios "
           "(A10) ocurriera antes de cerrar el modelo de datos: así el feedback afecta el diseño y no "
           "el código. La segunda fue ejecutar en paralelo la seguridad (A13 a A15) con el modelo de "
           "datos, ya que ambas dependen de la arquitectura y ninguna bloquea el informe.")

    h3(doc, "Prioridades del backlog")
    p(doc, "La priorización combina MoSCoW con una matriz de valor para el negocio frente a esfuerzo "
           "de implementación (Figura 3). Sobre las catorce historias heredadas del ES1, ocho son "
           "imprescindibles para el producto mínimo, tres deberían estar y tres podrían. No se "
           "declara ninguna historia fuera del backlog: lo que queda excluido del alcance es la "
           "integración con el ERP corporativo y la aplicación móvil nativa, que no forman parte del "
           "diagnóstico del equipo.")
    justificacion = {
        "HU-OP-01": "Es la razón de ser del tablero del operador: sin la última inspección visible no "
                    "hay decisión operativa posible",
        "HU-OP-02": "Permite revisar la consistencia del turno; sin historial el operador depende de "
                    "la memoria",
        "HU-OP-03": "Anticipa el rechazo, pero el flujo mínimo funciona sin ella: RF-07 puede "
                    "activarse después del núcleo",
        "HU-SU-01": "El supervisor necesita indicadores para monitorear el proceso; materializa la "
                    "necesidad N3",
        "HU-SU-02": "Es la funcionalidad central de trazabilidad: filtros avanzados y exportación del "
                    "histórico",
        "HU-SU-03": "Aporta contexto por lote y complementa el histórico, sin reemplazarlo",
        "HU-SU-04": "Automatiza la entrega de información, pero la consulta manual ya cubre la "
                    "necesidad",
        "HU-AD-01": "Sin gestión de usuarios y roles no existe control de acceso (N5) ni trazabilidad "
                    "de autoría",
        "HU-AD-02": "Las tolerancias de la receta determinan el estado de cada inspección: es parte "
                    "del núcleo del negocio",
        "HU-AD-03": "La estructura lote/batch es el contexto que hace trazable cada medición",
        "HU-AD-04": "Los parámetros tienen valores por defecto; ajustarlos es una mejora, no un "
                    "requisito del flujo",
        "HU-SC-01": "Es la entrada de datos del sistema: sin la API no existe inspección que registrar",
        "HU-SC-02": "La confirmación con identificador evita duplicados y pérdidas en el sistema de "
                    "visión",
        "HU-CA-01": "El área de calidad requiere reportes para auditoría; importante, pero posterior "
                    "al núcleo",
    }
    tabla(doc,
          ["Historia", "Prioridad", "Justificación de la prioridad"],
          [(h[0], h[5], justificacion[h[0]]) for h in D.HU],
          anchos=[2.0, 2.0, 12.8], fs=8.4,
          titulo="Priorización del backlog con MoSCoW", resaltar_col0=True)

    figura(doc, "04_priorizacion_moscow.png", 14.6,
           "Matriz de priorización del backlog: valor para el negocio frente a esfuerzo",
           "Los cuadrantes traducen MoSCoW a una decisión de secuencia: primero lo valioso y barato, "
           "después lo valioso y costoso; lo barato y poco valioso solo si sobra capacidad.")

    h3(doc, "Riesgos del cronograma")
    tabla(doc,
          ["ID", "Riesgo", "Prob.", "Impacto", "Mitigación", "Responsable"],
          D.RIESGOS,
          anchos=[1.1, 4.6, 1.4, 1.4, 6.0, 2.3], fs=8.0,
          titulo="Registro de riesgos del proyecto y su mitigación", resaltar_col0=True)


# --------------------------------------------------------------------------- #
# 2.1.2
# --------------------------------------------------------------------------- #
def seccion_212(doc):
    h1(doc, "2.1.2  Arquitectura de la solución")

    p(doc, "La arquitectura se documenta con el paradigma 4+1 porque permite describir el mismo "
           "sistema desde cinco perspectivas complementarias y verificar que todas cuentan la misma "
           "historia, que es el propósito original del modelo (Kruchten, 1995). Para este proyecto la "
           "decisión estructural más importante fue construir un "
           "monolito modular -una sola aplicación desplegable con fronteras internas claras- en lugar "
           "de microservicios: con tres desarrolladores y un semestre, la complejidad operativa de los "
           "microservicios habría consumido el tiempo destinado a resolver el problema del negocio.")

    # ---- 2.1.2.3 ----
    h2(doc, "2.1.2.3  Puntos de vista del paradigma 4+1")
    criterio(doc, "2.1.2.3", "Destacado (5 puntos)",
             "Todos los puntos de vista definidos con precisión y detalle, totalmente alineados a la "
             "solución y a la infraestructura.")

    p(doc, "La Tabla 11 resume el propósito de cada vista, el artefacto que la materializa y su "
           "vínculo con los requisitos. Las subsecciones siguientes desarrollan cada una.")

    tabla(doc,
          ["Vista", "Propósito", "Artefacto que la materializa", "Requisitos vinculados"],
          D.VISTAS,
          anchos=[2.4, 5.6, 5.2, 3.6], fs=8.4,
          titulo="Las cinco vistas del paradigma 4+1 y su trazabilidad", resaltar_col0=True)

    h3(doc, "Contexto del sistema")
    p(doc, "Antes de las cinco vistas conviene fijar el alcance: qué actores usan el sistema y con qué "
           "sistemas externos se comunica. El sistema web no procesa imágenes ni se conecta a la "
           "maquinaria: recibe la medición ya calculada por el sistema de visión existente (o por un "
           "simulador) y la convierte en información trazable.")
    figura(doc, "05_contexto_c4.png", 15.8,
           "Contexto del sistema y sus integraciones externas",
           "El sistema de captura envía la medición por HTTPS con un token de servicio; el resto de los "
           "actores interactúan desde el navegador.")

    h3(doc, "Vista de escenarios (casos de uso)")
    p(doc, "Los escenarios son la vista que valida a las otras cuatro: si una decisión de arquitectura "
           "no permite ejecutar un caso de uso, la arquitectura está mal. Se identificaron doce casos "
           "de uso agrupados por actor y seis escenarios expandidos que se detallan en el Anexo A.")
    figura(doc, "06_casos_uso.png", 16.0,
           "Diagrama de casos de uso del sistema",
           "Cada actor se ubica en la fila de los casos de uso que le corresponden, de modo que las "
           "asociaciones no se crucen. UC-11 se incluye en UC-10, UC-06 extiende UC-05 y UC-12 notifica "
           "hacia el servicio SMTP que administra el reporte.")

    tabla(doc,
          ["Código", "Caso de uso", "Actor primario", "Propósito", "Requisitos", "Pantalla del prototipo"],
          D.CASOS_USO,
          anchos=[1.4, 3.4, 3.2, 4.2, 2.4, 2.2], fs=7.6,
          titulo="Catálogo de casos de uso y su trazabilidad", resaltar_col0=True)

    h3(doc, "Vista lógica")
    p(doc, "La vista lógica describe los componentes funcionales y sus dependencias. Se adoptó una "
           "arquitectura en capas con dependencias unidireccionales: presentación, API, servicios, "
           "repositorios y modelos. La regla es que una capa solo puede depender de la inmediatamente "
           "inferior; en particular, solo los repositorios ejecutan SQL y solo los servicios contienen "
           "reglas de negocio.")
    figura(doc, "07_vista_logica.png", 16.2,
           "Vista lógica: componentes, capas y almacenes de datos",
           "Las flechas discontinuas hacia los almacenes representan acceso a datos: la API y los "
           "servicios nunca hablan directamente con PostgreSQL sin pasar por un repositorio.")

    p(doc, "Esta separación no es decorativa: permite probar las reglas de tolerancia sin base de "
           "datos ni HTTP, que es precisamente lo que exige el plan de pruebas del capítulo 2.1.6. "
           "También aísla el cambio: si mañana se reemplaza PostgreSQL por otro motor, el impacto queda "
           "confinado a la capa de repositorios.")

    h3(doc, "Vista de desarrollo")
    p(doc, "La vista de desarrollo explica cómo se organiza el código físico. Se optó por un monorepo "
           "con dos aplicaciones (backend y frontend) y módulos compartidos, porque con tres "
           "integrantes la coordinación entre repositorios separados tiene un costo mayor que el "
           "beneficio del aislamiento.")
    figura(doc, "08_vista_desarrollo.png", 16.0,
           "Vista de desarrollo: estructura del repositorio y regla de dependencia entre capas",
           "Cada rama sigue la convención feature/HU-<n>-<descripción> y se integra mediante pull "
           "request revisado por un par.")

    h3(doc, "Vista de procesos")
    p(doc, "La vista de procesos describe el comportamiento en ejecución. El escenario crítico es el "
           "registro de una inspección, porque ocurre muchas veces por turno y su latencia afecta la "
           "operación. La secuencia muestra dos decisiones relevantes: la transacción que abarca la "
           "lectura de la receta y la escritura de la inspección, y el trabajo asíncrono que deja el "
           "envío de alertas fuera del ciclo de la petición.")
    figura(doc, "09_vista_procesos.png", 16.2,
           "Vista de procesos: secuencia del registro de una inspección",
           "Los pasos 1 a 8 son síncronos y transaccionales; el envío de correo se encola y se ejecuta "
           "en el trabajador asíncrono, de modo que la respuesta al sistema de captura no dependa de "
           "un servicio externo.")

    h3(doc, "Vista física")
    p(doc, "La vista física indica dónde se ejecuta el software. La solución se despliega en un único "
           "servidor virtual con contenedores, lo que reduce el costo y mantiene la reproducibilidad. "
           "La base de datos y el almacenamiento de objetos usan volúmenes persistentes, y los "
           "respaldos se envían cifrados a un bucket en una región distinta.")
    figura(doc, "10_vista_fisica.png", 16.2,
           "Vista física: despliegue en contenedores sobre un servidor virtual",
           "La API y el trabajador asíncrono pueden escalar en réplicas sin cambiar el modelo de datos; "
           "el respaldo externo cubre el requisito RNF-02 (disponibilidad).")

    h3(doc, "Decisiones de arquitectura y su justificación")
    tabla(doc,
          ["Decisión", "Alternativa descartada", "Motivo de la elección", "Consecuencia asumida"],
          [("Monolito modular con capas", "Microservicios por dominio",
            "Tres integrantes y un semestre: la complejidad operativa de los microservicios supera el "
            "beneficio en este alcance",
            "Si un módulo crece, se extrae después con fronteras ya definidas"),
           ("API REST con contrato OpenAPI", "GraphQL",
            "El consumo es simple y predecible; OpenAPI da documentación y pruebas automáticas",
            "Consultas del dashboard requieren endpoints específicos"),
           ("Trabajo asíncrono con cola", "Todo síncrono",
            "El envío de correo no debe degradar el tiempo de respuesta del registro",
            "Hay que operar un trabajador y monitorear la cola"),
           ("Almacenamiento de objetos externo", "Imágenes como BLOB en la base",
            "Los archivos grandes degradan las consultas y los respaldos",
            "Se requiere gestionar la coherencia entre la BD y el objeto"),
           ("Copia de límites en la inspección", "Normalización estricta",
            "RNF-10 (integridad de datos) exige conservar los límites aplicados aunque la receta cambie",
            "Se acepta una redundancia controlada y documentada")],
          anchos=[3.6, 3.4, 5.8, 4.0], fs=8.2,
          titulo="Decisiones de arquitectura con justificación y consecuencias",
          resaltar_col0=True)

    # ---- 2.1.2.4 ----
    h2(doc, "2.1.2.4  Tecnologías y herramientas de la infraestructura")
    criterio(doc, "2.1.2.4", "Destacado (5 puntos)",
             "Identificación exhaustiva y justificada de tecnologías y herramientas, considerando "
             "necesidades futuras.")

    p(doc, "La selección de tecnología se sometió a tres criterios explícitos: que el equipo pudiera "
           "operarla sin curva de aprendizaje incompatible con el plazo, que resolviera un problema "
           "concreto del dominio y que fuera reemplazable sin rehacer la arquitectura. El estilo REST de la "
           "API responde a las restricciones de interfaz uniforme y ausencia de estado descritas "
           "por Fielding (2000), y su contrato se documenta con OpenAPI (Richardson & Ruby, "
           "2007). La Tabla 14 "
           "enumera el stack completo, su justificación y la alternativa que se descartó.")

    tabla(doc,
          ["Capa", "Tecnología", "Función", "Justificación", "Alternativa descartada"],
          D.TECNOLOGIAS,
          anchos=[2.2, 3.6, 2.2, 5.6, 3.2], fs=7.8,
          titulo="Stack tecnológico e infraestructura con justificación de cada elección",
          resaltar_col0=True)

    h3(doc, "Requerimientos de infraestructura")
    tabla(doc,
          ["Componente", "Especificación mínima", "Justificación"],
          [("Servidor virtual", "4 vCPU, 8 GB de RAM, 100 GB SSD", "Suficiente para la API, el worker, "
                                                                   "PostgreSQL, Redis y MinIO en un host"),
           ("Sistema operativo", "Ubuntu 24.04 LTS", "Soporte de largo plazo y disponibilidad de "
                                                     "paquetes actualizados"),
           ("Red", "IP pública, puertos 80 y 443; SSH restringido por IP",
            "Solo se expone el proxy; los servicios internos no son accesibles desde fuera"),
           ("Almacenamiento externo", "Bucket S3 con cifrado del lado del servidor",
            "Respaldo fuera del proveedor principal, requisito RNF-02"),
           ("Dominio y certificados", "Dominio propio y certificado TLS 1.3 (Let's Encrypt)",
            "Cifrado en tránsito y acceso estable para la contraparte"),
           ("Monitoreo", "Health checks y alertas de disponibilidad",
            "Verifica RNF-02 con evidencia medible")],
          anchos=[3.6, 5.6, 7.6], fs=8.4,
          titulo="Requerimientos de infraestructura del despliegue", resaltar_col0=True)

    h3(doc, "Necesidades futuras consideradas")
    bullets(doc, [
        ("Escalabilidad horizontal: ", "la API y el trabajador se ejecutan en contenedores sin estado, "
         "por lo que agregar réplicas no requiere cambios de código."),
        ("Crecimiento del histórico: ", "los índices parciales y la paginación por cursor permiten "
         "sostener el rendimiento cuando el volumen se multiplique por diez."),
        ("Integración con el ERP: ", "la API expone un contrato versionado que permite agregar "
         "sincronización con el ERP corporativo sin romper a los consumidores actuales; esa integración "
         "queda fuera del alcance del desafío."),
        ("Observabilidad: ", "los logs estructurados y el identificador de correlación permiten "
         "diagnosticar incidentes cuando el sistema esté en operación real."),
        ("Costo: ", "la estimación de infraestructura mensual se mantiene en el rango de un servidor "
         "virtual y un bucket, sin licencias propietarias."),
    ])


# --------------------------------------------------------------------------- #
# 2.1.3
# --------------------------------------------------------------------------- #
def seccion_213(doc):
    h1(doc, "2.1.3  Prototipado y experiencia de usuario")

    # ---- 2.1.3.5 ----
    h2(doc, "2.1.3.5  Prototipos interactivos funcionales")
    criterio(doc, "2.1.3.5", "Destacado (5 puntos)",
             "Prototipo completamente funcional, representando cada interacción clave; alineado a las "
             "necesidades del negocio.")
    evidencia(doc, "Prototipo navegable en HTML (archivo independente) y Figuras 10 a 14 con las "
                   "pantallas principales.")

    p(doc, "El prototipo no es un conjunto de imágenes estáticas: es una aplicación HTML, CSS y "
           "JavaScript autocontenida que se abre en cualquier navegador y permite navegar entre las "
           "seis pantallas del sistema, filtrar la tabla del histórico y observar los estados de la "
           "inspección. Se entregó junto con este informe como archivo independiente "
           "(prototipo/aza-prototipo.html) para que la evaluación pueda ejecutarlo.")

    p(doc, "La decisión de construirlo en HTML en lugar de una herramienta de wireframes tuvo una "
           "razón práctica: el mismo artefacto sirve como especificación visual para el equipo y como "
           "evidencia verificable para la evaluación, y permite comprobar de forma real la "
           "adaptabilidad a distintos tamaños de pantalla.")

    h3(doc, "Pantallas y flujo de navegación")
    tabla(doc,
          ["Pantalla", "Propósito", "Interacciones clave", "Historias"],
          [("Login", "Autenticar al usuario y determinar su rol",
            "Selección de usuario, PIN enmascarado, mensaje de error genérico", "RF-11, HU-AD-01"),
           ("Dashboard", "Mostrar el estado del turno y la última inspección",
            "Actualización automática, indicadores, gráfico de tendencia", "HU-OP-01, HU-SU-01"),
           ("Histórico", "Consultar y filtrar inspecciones",
            "Filtros combinables, limpiar, exportar, paginación", "HU-OP-02, HU-SU-02, HU-CA-01"),
           ("Detalle", "Examinar una inspección y su trazabilidad",
            "Metadatos, imagen del diagnóstico, bitácora del registro", "HU-SU-03, RF-10"),
           ("Recetas", "Gestionar tolerancias por producto",
            "Alta y edición con aviso de inmutabilidad del histórico", "HU-AD-02, HU-AD-03"),
           ("Usuarios", "Administrar cuentas y roles",
            "Listado de usuarios y matriz de permisos visible", "HU-AD-01, RF-05"),
           ("Feedback", "Dejar constancia de la validación con usuarios",
            "Registro de observaciones y cambios aplicados", "Transversal")],
          anchos=[2.4, 4.6, 6.2, 3.6], fs=8.4,
          titulo="Pantallas del prototipo e interacciones cubiertas", resaltar_col0=True)

    figura(doc, "14_proto_login.png", 11.6,
           "Pantalla de inicio de sesión del prototipo interactivo",
           "Formulario accesible: etiquetas asociadas, foco visible y mensaje de ayuda bajo el campo "
           "de PIN.")

    figura(doc, "15_proto_dashboard.png", 16.2,
           "Dashboard del operador con indicadores del turno y última inspección",
           "El medidor angular, la etiqueta de estado y la barra de tolerancia responden a la "
           "observación FB-01 y FB-02 del registro de validación (Tabla 19).")

    figura(doc, "16_proto_historico.png", 16.2,
           "Pantalla de consulta histórica con filtros combinables",
           "Los filtros permanecen visibles sobre la tabla, tal como solicitó el supervisor en la "
           "observación FB-05.")

    figura(doc, "17_proto_detalle.png", 16.2,
           "Detalle de una inspección con su trazabilidad completa",
           "El bloque de bitácora responde a la observación FB-10: el usuario puede ver de dónde "
           "proviene el dato y qué ocurrió con él.")

    figura(doc, "18_proto_recetas.png", 15.0,
           "Gestión de recetas con tolerancias por producto",
           "El aviso de la parte superior comunica que editar una receta no altera los registros "
           "históricos (observación FB-08).")

    p(doc, "El prototipo incluye además una pantalla de usuarios con la matriz de permisos visible "
           "(observación FB-09) y una pantalla de feedback que documenta el proceso de validación. "
           "Ambas se incluyen en el inventario de evidencias del Anexo F.")

    # ---- 2.1.3.6 ----
    h2(doc, "2.1.3.6  Consistencia visual y adaptabilidad")
    criterio(doc, "2.1.3.6", "Destacado (5 puntos)",
             "Diseño consistente y adaptable, respetando guías de estilo y responsive para "
             "dispositivos.")
    evidencia(doc, "Tablas 17 y 18 (tokens y puntos de quiebre) y Figuras 11, 15 y 16 (escritorio, tablet "
                   "y móvil).")

    p(doc, "Un tablero operativo no es un reporte: su función es responder una pregunta en segundos, de "
           "modo que la jerarquía visual importa más que la cantidad de indicadores (Few, 2006; "
           "Shneiderman, 1996; Knaflic, 2015). La consistencia visual se garantiza con una guía de "
           "estilo materializada en variables CSS: "
           "ningún color, tamaño o espaciado se escribe dos veces con valores distintos. La elección de "
           "la paleta no es arbitraria: el verde institucional de Aceros AZA estructura la identidad, y "
           "los colores de estado se reservan exclusivamente para aprobado, rechazado y sin receta, de "
           "modo que un operador no confunda un color decorativo con una señal de calidad.")

    h3(doc, "Guía visual")
    tabla(doc,
          ["Elemento", "Token", "Valor", "Uso", "Contraste"],
          D.GUIA_VISUAL,
          anchos=[3.4, 3.6, 3.4, 4.4, 2.0], fs=8.2,
          titulo="Guía visual: colores, tipografía y espaciado del sistema", resaltar_col0=True)

    p(doc, "Todos los pares de texto y fondo cumplen el nivel AA de WCAG 2.1 (razón de contraste "
           "mínima 4,5:1 en texto normal). Además, y en línea con los criterios de accesibilidad del "
           "W3C (World Wide Web Consortium, 2018), el estado nunca se comunica solo con color: las "
           "etiquetas incluyen texto —«Aprobada», «Rechazada», «Sin receta»— y un punto de color, de "
           "modo que la interfaz siga siendo comprensible para una persona con daltonismo o para una "
           "fotografía en blanco y negro.")

    h3(doc, "Accesibilidad y consistencia de comportamiento")
    bullets(doc, [
        ("Foco visible: ", "todos los controles muestran un contorno de 3 px al recibir el foco por "
         "teclado; la navegación completa es posible sin mouse."),
        ("Etiquetas asociadas: ", "cada campo tiene su etiqueta vinculada y los mensajes de error se "
         "anuncian junto al campo, no solo con color."),
        ("Estados vacíos y de error: ", "la tabla muestra un estado vacío explícito cuando un filtro no "
         "devuelve resultados, en lugar de una tabla en blanco."),
        ("Movimiento reducido: ", "se respeta prefers-reduced-motion para desactivar transiciones."),
        ("Consistencia de acciones: ", "la acción principal de cada pantalla es siempre un botón verde "
         "sólido; las secundarias son botones con borde; las destructivas, rojas."),
        ("Jerarquía tipográfica única: ", "cuatro tamaños como máximo, con la misma escala en todas las "
         "pantallas."),
    ])

    h3(doc, "Adaptabilidad a dispositivos")
    p(doc, "La adaptabilidad no se resolvió reescalando la interfaz de escritorio, sino definiendo "
           "comportamientos distintos por rango de ancho. El cambio más importante ocurre en las "
           "tablas: bajo 860 px cada fila se convierte en una tarjeta con sus etiquetas, porque una "
           "tabla de ocho columnas es ilegible en un teléfono.")
    tabla(doc,
          ["Rango", "Ancho", "Comportamiento del diseño", "Dispositivo objetivo"],
          D.RESPONSIVE,
          anchos=[3.4, 2.6, 7.2, 3.6], fs=8.4,
          titulo="Puntos de quiebre y comportamiento del diseño responsive", resaltar_col0=True)

    figura(doc, "21_proto_tablet.png", 12.0,
           "Vista en tablet vertical (1024 px): la barra lateral y la tabla se reorganizan",
           "Los indicadores pasan a dos columnas y las vistas de dos paneles se apilan.")

    figura(doc, "22_proto_movil.png", 7.4,
           "Vista en móvil (390 px): navegación superior desplazable y tarjetas apiladas",
           "Los filtros y las tablas se transforman en bloques verticales; se mantiene la jerarquía "
           "del ángulo y del estado.")

    # ---- 2.1.3.7 ----
    h2(doc, "2.1.3.7  Integración de la retroalimentación de usuarios")
    criterio(doc, "2.1.3.7", "Destacado (5 puntos)",
             "Retroalimentación completamente integrada, resultando en un diseño refinado y funcional.")
    evidencia(doc, "Tabla 19 (11 observaciones con su cambio aplicado) y Figura 17 (registro de "
                   "validación dentro del prototipo).")

    p(doc, "La validación se organizó en dos rondas. En la primera se trabajó con los perfiles de "
           "operador y supervisor de calidad, con el prototipo v1 en pantalla y una guía de tareas "
           "concretas: encontrar el resultado de la última inspección, filtrar un lote y determinar si "
           "un valor estaba dentro de tolerancia. En la segunda ronda se validó con el perfil de "
           "administrador y con el docente contraparte, ya sobre el prototipo v2.")

    p(doc, "El criterio para aceptar una observación fue doble: que describiera un obstáculo real en "
           "una tarea y que pudiera resolverse sin alterar la arquitectura. Las observaciones que "
           "implicaban cambios estructurales mayores se registraron como candidatas para el Sprint 4, "
           "no se descartaron.")

    tabla(doc,
          ["ID", "Ronda", "Participante", "Observación", "Decisión de diseño", "Cambio aplicado", "Estado"],
          D.FEEDBACK,
          anchos=[1.1, 1.0, 2.4, 3.8, 3.6, 3.4, 1.5], fs=7.4,
          titulo="Registro de retroalimentación y cambios aplicados al prototipo", resaltar_col0=True)

    figura(doc, "20_proto_feedback.png", 16.0,
           "Pantalla de feedback del prototipo: de la observación al cambio aplicado",
           "El prototipo incluye esta pantalla para que la trazabilidad de la validación sea visible "
           "también durante la demostración.")

    h3(doc, "Síntesis del refinamiento")
    p(doc, "De las once observaciones registradas, nueve se aplicaron en la versión 2 y dos quedaron en "
           "revisión. Los cambios con mayor impacto fueron tres: el ángulo pasó a mostrarse con una "
           "cifra dominante y su estado al lado (FB-01), la tolerancia dejó de ser un dato que había "
           "que memorizar y se convirtió en una barra de rango visible (FB-02), y los filtros dejaron "
           "de estar ocultos en un panel lateral (FB-05). Los tres apuntan a la misma lección: el "
           "operador necesita decidir en segundos, no explorar la interfaz.")


# --------------------------------------------------------------------------- #
# 2.1.4
# --------------------------------------------------------------------------- #
def seccion_214(doc):
    h1(doc, "2.1.4  Modelo de datos")

    p(doc, "El modelo de datos traduce las reglas de negocio del trefilado a estructuras "
           "verificables, equilibrando normalización y rendimiento de lectura (Kleppmann, 2017). "
           "verificables. La decisión de diseño más importante fue separar el catálogo de recetas del "
           "hecho registrado: la inspección guarda una copia de los límites con los que fue evaluada. "
           "Sin esa separación, cambiar una tolerancia reescribiría el significado del histórico, que "
           "es exactamente lo que un sistema de trazabilidad no debe permitir.")

    # ---- 2.1.4.8 ----
    h2(doc, "2.1.4.8  Entidades y relaciones")
    criterio(doc, "2.1.4.8", "Destacado (10 puntos)",
             "Modelo completo y optimizado; incluye integridad referencial y claves primarias y "
             "secundarias.")
    evidencia(doc, "Figura 18 (DER con 10 entidades), Tabla 20 (diccionario de datos), Tabla 21 "
                   "(normalización) y Tabla 22 (índices).")

    figura(doc, "11_der.png", 16.4,
           "Modelo entidad-relación del sistema, normalizado en tercera forma normal",
           "Todas las relaciones son 1:N. Las claves primarias se marcan como PK, las foráneas como FK "
           "y los valores únicos como UK.")

    p(doc, "El modelo tiene diez entidades organizadas en tres grupos: seguridad (roles, usuarios, "
           "sesiones), contexto de producción (recetas, lotes, batches) y hechos (inspecciones, "
           "imágenes, alarmas, auditoría). La entidad central es «inspecciones», que relaciona el hecho "
           "medido con su contexto y con el operador que lo generó.")

    h3(doc, "Diccionario de datos")
    filas = []
    for entidad, desc, campos in D.ENTIDADES:
        for nombre, tipo, clave, descripcion in campos:
            filas.append((entidad, nombre, tipo, clave, descripcion))
    tabla(doc,
          ["Entidad", "Atributo", "Tipo", "Clave", "Descripción"],
          filas,
          anchos=[2.6, 3.2, 3.4, 2.4, 5.2], fs=7.4,
          titulo="Diccionario de datos: atributos, tipos y restricciones",
          resaltar_col0=True)

    h3(doc, "Integridad referencial")
    p(doc, "Las políticas de borrado se eligieron por entidad, no de forma global. En los catálogos "
           "maestros se usa RESTRICT: no se puede borrar una receta que tenga inspecciones asociadas, "
           "porque eso destruiría trazabilidad. En las entidades dependientes de un hecho se usa "
           "CASCADE: si se elimina una inspección por una depuración autorizada, sus imágenes y "
           "alarmas asociadas dejan de tener sentido. Las sesiones se eliminan en cascada al borrar un "
           "usuario, porque no constituyen evidencia de negocio.")

    h3(doc, "Normalización")
    tabla(doc,
          ["Forma", "Regla", "Cómo se evidencia en el modelo"],
          D.NORMALIZACION,
          anchos=[2.4, 4.4, 10.0], fs=8.2,
          titulo="Evidencia de normalización del modelo y excepciones justificadas",
          resaltar_col0=True)

    h3(doc, "Índices y optimización")
    tabla(doc,
          ["Índice", "Definición", "Consulta que optimiza"],
          D.INDICES,
          anchos=[3.8, 6.4, 6.6], fs=8.2,
          titulo="Índices definidos y consulta que optimiza cada uno", resaltar_col0=True)

    p(doc, "Los índices parciales son la decisión de optimización más importante: la consulta de "
           "alertas solo busca registros no aprobados, que son una minoría del total. Un índice "
           "parcial sobre esas filas ocupa una fracción del espacio de un índice completo y responde "
           "más rápido, porque no indexa los 300 registros aprobados de cada turno.")

    h3(doc, "Ciclo de vida del registro")
    figura(doc, "03_estados_inspeccion.png", 16.0,
           "Máquina de estados del objeto «Inspección»",
           "Transiciones T1 a T9: el estado se calcula una sola vez con la receta vigente y el registro "
           "pasa a solo lectura cuando se archiva.")

    # ---- 2.1.4.9 ----
    h2(doc, "2.1.4.9  Bases de datos estructuradas y no estructuradas")
    criterio(doc, "2.1.4.9", "Destacado (5 puntos)",
             "Uso eficaz de bases estructuradas y no estructuradas con ejemplos funcionales.")
    evidencia(doc, "Tabla 23 (criterio de asignación por tipo de dato) y Anexo B (DDL ejecutable con "
                   "columnas JSONB y referencia a objetos).")

    p(doc, "No todos los datos del sistema son iguales y tratarlos igual sería un error de diseño. Los "
           "datos que se filtran, se ordenan y se agregan —inspecciones, recetas, lotes— son "
           "estructurados y pertenecen a una base relacional. Los archivos binarios —las imágenes de "
           "cada ráfaga— no deben vivir en la base: guardarlos como BLOB multiplicaría el tamaño de los "
           "respaldos y degradaría las consultas. La solución usa ambos tipos de almacenamiento y "
           "declara explícitamente qué va en cada uno.")

    tabla(doc,
          ["Dato", "Almacenamiento", "Clasificación", "Justificación"],
          D.SQL_VS_NO_SQL,
          anchos=[3.6, 3.8, 3.0, 6.4], fs=8.2,
          titulo="Criterio de asignación entre base estructurada y no estructurada",
          resaltar_col0=True)

    h3(doc, "Ejemplo funcional: imágenes de una ráfaga")
    p(doc, "Cuando el sistema de captura envía una inspección con imágenes, se ejecutan tres pasos: "
           "(1) cada archivo se sube a MinIO con una clave construida como "
           "lotes/<año>/<lote>/<trigger>/img_<n>.bmp; (2) se calcula el SHA-256 del archivo; (3) se "
           "inserta en «imagenes» la referencia con la clave, el tamaño y el checksum. La base de datos "
           "nunca contiene el binario, pero conserva la prueba de integridad: si el archivo cambia o "
           "desaparece, el checksum lo delata.")

    h3(doc, "Ejemplo funcional: dato semiestructurado en JSONB")
    p(doc, "La bitácora de auditoría registra cambios de entidades distintas —una receta, un usuario, "
           "una inspección— cuyos campos no coinciden entre sí. En lugar de crear una tabla de "
           "auditoría por entidad, la columna «detalle» de tipo JSONB guarda los valores anteriores y "
           "posteriores del cambio. PostgreSQL permite consultarlos con operadores JSON, por ejemplo "
           "para responder «qué recetas cambiaron su tolerancia máxima este mes», sin renunciar a la "
           "estructura común de la bitácora (autor, fecha, entidad, acción).")

    h3(doc, "Políticas de retención")
    tabla(doc,
          ["Tipo de dato", "Retención", "Acción al vencer"],
          [("Inspecciones", "24 meses en línea", "Archivado a almacenamiento frío; se conserva el "
                                                 "agregado para indicadores"),
           ("Imágenes de ráfaga", "6 meses", "Purga del objeto en MinIO; se conserva el registro con su "
                                             "checksum"),
           ("Auditoría", "36 meses", "Se conserva; es requisito de trazabilidad"),
           ("Exportaciones CSV", "30 días", "Purga automática del objeto generado"),
           ("Respaldos", "30 días", "Rotación automática según política del proveedor")],
          anchos=[3.6, 3.2, 10.0], fs=8.4,
          titulo="Políticas de retención por tipo de dato", resaltar_col0=True)

    p(doc, "Nota académica: los plazos de retención son una propuesta del equipo. La documentación de "
           "la empresa no especifica una política oficial, y el desafío indica expresamente que este "
           "aspecto debe validarse con la contraparte durante ES1 y ES2.")


# --------------------------------------------------------------------------- #
# 2.1.5
# --------------------------------------------------------------------------- #
def seccion_215(doc):
    h1(doc, "2.1.5  Seguridad de la información")

    p(doc, "La seguridad se aborda en tres niveles complementarios: quién puede entrar y qué puede "
           "hacer (autenticación y autorización), a qué está expuesto el sistema (amenazas y "
           "mitigaciones) y cómo se escribe el código (estándares). Separarlos permite que cada "
           "control tenga un responsable y una verificación concreta.")

    # ---- 2.1.5.10 ----
    h2(doc, "2.1.5.10  Políticas de autenticación y autorización")
    criterio(doc, "2.1.5.10", "Destacado (10 puntos)",
             "Políticas robustas, específicas y alineadas con las mejores prácticas; cubren roles y "
             "perfiles.")
    evidencia(doc, "Tabla 25 (política de autenticación), Tabla 26 (matriz de permisos por rol) y "
                   "Tabla 27 (autorización por endpoint).")

    p(doc, "El control de acceso basado en roles asigna permisos a los roles y no a las personas, lo que "
           "reduce el error operativo y hace auditable la autorización (Sandhu et al., 1996); los "
           "lineamientos de identidad digital recomiendan credenciales de vigencia corta con "
           "verificación en el servidor (National Institute of Standards and Technology, 2020). "
           "La política se diseñó con dos principios: el servidor decide siempre —el cliente nunca es "
           "autoridad de permisos— y la sesión es efímera por defecto. En un entorno de planta el "
           "riesgo concreto no es un atacante remoto sofisticado, sino el uso indebido de una sesión "
           "abierta en una pantalla compartida y el robo de un token de larga duración.")

    tabla(doc,
          ["Aspecto", "Política adoptada", "Justificación"],
          D.AUTENTICACION,
          anchos=[3.4, 6.6, 6.8], fs=8.2,
          titulo="Política de autenticación y gestión de sesión", resaltar_col0=True)

    h3(doc, "Roles y matriz de autorización")
    p(doc, "Se definieron cuatro roles. El cuarto —integrador— no es una persona: es la cuenta de "
           "servicio que usa el sistema de captura y que solo puede invocar el endpoint de registro. "
           "Separarlo de los roles humanos es lo que impide que una credencial de máquina pueda "
           "consultar el histórico o modificar recetas.")
    tabla(doc,
          ["Acción", "Operador", "Supervisor", "Administrador"],
          D.ROLES_MATRIZ,
          anchos=[7.6, 3.0, 3.1, 3.1], fs=8.4,
          titulo="Matriz de autorización por rol (RBAC)", resaltar_col0=True)

    tabla(doc,
          ["Método", "Endpoint", "Roles autorizados", "Observación"],
          D.AUTORIZACION_ENDPOINTS,
          anchos=[1.8, 5.4, 4.2, 5.4], fs=7.8,
          titulo="Autorización por endpoint de la API", resaltar_col0=True)

    p(doc, "La verificación de rol ocurre en una dependencia de FastAPI que se ejecuta antes del "
           "controlador, de modo que es imposible olvidarla al agregar un endpoint nuevo: si el "
           "desarrollador no declara los roles permitidos, la petición se rechaza por defecto. Es el "
           "principio de denegación por defecto aplicado a nivel de código.")

    # ---- 2.1.5.11 ----
    h2(doc, "2.1.5.11  Amenazas comunes y medidas de mitigación")
    criterio(doc, "2.1.5.11", "Destacado (10 puntos)",
             "Identificación exhaustiva con medidas de mitigación bien documentadas.")
    evidencia(doc, "Figura 20 (defensa en profundidad) y Tabla 28 (12 amenazas con su control y su "
                   "requisito asociado).")

    p(doc, "El análisis usó dos marcos complementarios: STRIDE para clasificar las amenazas por tipo de "
           "fallo y OWASP Top 10 como referencia de las vulnerabilidades más frecuentes en "
           "aplicaciones web (OWASP Foundation, 2021). Para cada amenaza se identificó el activo afectado, "
           "el control concreto y "
           "el requisito que lo respalda, de manera que ninguna mitigación quede como una intención "
           "sin implementación asociada.")

    figura(doc, "13_capas_seguridad.png", 16.0,
           "Defensa en profundidad: cuatro capas de control y las amenazas que detiene cada una",
           "Ninguna capa por sí sola garantiza la seguridad; el diseño asume que un atacante puede "
           "superar una y debe encontrar otra adelante.")

    tabla(doc,
          ["Categoría", "Amenaza concreta en este sistema", "Medida de mitigación", "Requisito"],
          D.AMENAZAS,
          anchos=[3.2, 4.6, 6.2, 2.8], fs=7.8,
          titulo="Catálogo de amenazas, medidas de mitigación y requisito asociado",
          resaltar_col0=True)

    h3(doc, "Priorización del riesgo")
    p(doc, "No todas las amenazas merecen la misma inversión. Las dos de mayor prioridad son la "
           "manipulación de mediciones y la elevación de privilegios, porque afectan directamente la "
           "razón de ser del sistema: si un registro puede alterarse sin dejar rastro, la trazabilidad "
           "es una ilusión. Ambas se atacan con controles de bajo costo y alto impacto (inmutabilidad "
           "del registro, auditoría y verificación de rol en el servidor). En el extremo opuesto, el "
           "riesgo de denegación de servicio se mitiga de forma proporcional: límites de tasa y "
           "monitoreo, sin invertir en infraestructura de mitigación DDoS, que excede el alcance del "
           "proyecto.")

    # ---- 2.1.5.12 ----
    h2(doc, "2.1.5.12  Estándares de codificación segura")
    criterio(doc, "2.1.5.12", "Destacado (10 puntos)",
             "Estándares bien documentados, implementados y alineados a buenas prácticas.")
    evidencia(doc, "Tabla 29 (diez estándares con su herramienta de verificación) y la sección de "
                   "convenciones de código.")

    p(doc, "Un estándar que no se verifica automáticamente es una recomendación, no un estándar. Por "
           "eso cada práctica de la Tabla 29 tiene una herramienta asociada que la comprueba en el "
           "pipeline: si el código no cumple, la integración se detiene. La premisa es que la seguridad se "
           "incorpora durante el desarrollo y no al final del ciclo (McGraw, 2006). La regla es "
           "simple y "
           "explícita: ninguna rama se integra con análisis estático en rojo.")

    tabla(doc,
          ["Categoría", "Estándar definido", "Herramienta o mecanismo", "Verificación"],
          D.ESTANDARES_SEGUROS,
          anchos=[2.8, 6.2, 3.8, 4.0], fs=7.8,
          titulo="Estándares de codificación segura y su mecanismo de verificación",
          resaltar_col0=True)

    h3(doc, "Convenciones de código y de repositorio")
    bullets(doc, [
        ("Nombres: ", "snake_case en Python, camelCase en TypeScript, PascalCase para componentes y "
         "clases; las tablas y columnas en español singular, coherentes con el dominio."),
        ("Funciones: ", "máximo 40 líneas y una sola responsabilidad; las reglas de negocio viven en "
         "los servicios, nunca en los controladores."),
        ("Manejo de errores: ", "excepciones de dominio explícitas; prohibido el except desnudo; los "
         "errores internos se registran con identificador de correlación y se devuelve un mensaje "
         "genérico."),
        ("Commits: ", "formato convencional (feat, fix, test, docs, refactor) con referencia a la "
         "historia de usuario."),
        ("Ramas: ", "main protegida; una rama por historia (feature/HU-AD-02-recetas); integración solo "
         "por pull request con al menos una revisión."),
        ("Configuración: ", "todo valor variable por entorno se lee de variables de entorno; el "
         "repositorio incluye un archivo de ejemplo, nunca el archivo real."),
        ("Dependencias: ", "versiones fijadas en lockfile; agregar una dependencia requiere justificar "
         "su necesidad en el pull request."),
    ])


# --------------------------------------------------------------------------- #
# 2.1.6
# --------------------------------------------------------------------------- #
def seccion_216(doc):
    h1(doc, "2.1.6  Aseguramiento de la calidad y defensa")

    # ---- 2.1.6.13 ----
    h2(doc, "2.1.6.13  Pruebas unitarias, integrales y de rendimiento")
    criterio(doc, "2.1.6.13", "Destacado (10 puntos)",
             "Plan de pruebas completo y ejecutado, con resultados bien documentados.")
    evidencia(doc, "Figura 21 (pirámide de pruebas), Tabla 30 (22 casos con su criterio de aceptación), "
                   "Tabla 31 (umbrales de rendimiento) y Tabla 32 (resultados del equipo).")

    p(doc, "El plan de pruebas se organiza en cuatro niveles y se vincula a los requisitos: cada caso "
           "tiene un identificador, el requisito que verifica, la herramienta que lo ejecuta y el "
           "criterio con el que se considera aprobado; las pruebas se derivan del requisito y de "
           "sus condiciones de borde, no de la implementación (Myers et al., 2011). "
           "criterio con el que se considera aprobado. Esa trazabilidad es la que permite afirmar, al "
           "cierre, no solo que las pruebas pasan, sino qué parte del sistema está efectivamente "
           "verificada.")

    figura(doc, "12_piramide_pruebas.png", 15.4,
           "Estrategia de pruebas por nivel: cantidad de casos, herramienta y criterio",
           "La base de la pirámide concentra el volumen de pruebas automatizadas; la cima corresponde a "
           "validación manual con usuarios.")

    tabla(doc,
          ["ID", "Tipo", "Objetivo de la prueba", "Requisito", "Herramienta", "Criterio de aceptación",
           "Ejecución"],
          D.PLAN_PRUEBAS,
          anchos=[1.2, 1.7, 4.4, 2.0, 2.7, 3.4, 1.4], fs=7.2,
          titulo="Plan de pruebas: 22 casos trazados a requisitos y criterios de aceptación",
          resaltar_col0=True)

    h3(doc, "Umbrales de rendimiento")
    p(doc, "La empresa no entregó cifras oficiales de volumen ni de frecuencia de inspecciones. Los "
           "umbrales de la Tabla 31 se construyeron a partir de supuestos declarados explícitamente "
           "como académicos, tal como exige el desafío, para que puedan recalcularse cuando la "
           "contraparte entregue los datos reales.")
    tabla(doc,
          ["Escenario", "Umbral objetivo", "Condición de carga", "Base del supuesto"],
          D.UMBRALES,
          anchos=[3.6, 3.2, 3.8, 6.2], fs=8.2,
          titulo="Umbrales de rendimiento y supuestos de carga", resaltar_col0=True)

    h3(doc, "Resultados ya obtenidos por el equipo")
    p(doc, "Aunque la plataforma web se construye en ES3, el equipo ya cuenta con evidencia de práctica "
           "en pruebas automatizadas sobre el sistema de planta existente, lo que respalda la "
           "viabilidad del plan propuesto.")
    tabla(doc,
          ["Evidencia", "Qué se hizo", "Resultado obtenido", "Lectura para este proyecto"],
          D.RESULTADOS_EQUIPO,
          anchos=[3.4, 4.4, 4.6, 4.4], fs=8.0,
          titulo="Evidencia de práctica del equipo en pruebas automatizadas", resaltar_col0=True)

    h3(doc, "Criterios de entrada y salida")
    tabla(doc,
          ["Momento", "Criterio"],
          [("Entrada a pruebas de integración", "El análisis estático está limpio y las pruebas "
                                                "unitarias del módulo pasan al 100 %"),
           ("Entrada a pruebas de rendimiento", "El escenario funcional equivalente ya pasó en "
                                                "integración"),
           ("Entrada a UAT", "No hay defectos de severidad alta o crítica abiertos"),
           ("Salida de ES3", "Cobertura ≥ 70 % global, umbrales de rendimiento cumplidos y cero "
                             "defectos críticos abiertos"),
           ("Registro de defectos", "Todo defecto se documenta con pasos de reproducción, severidad y "
                                    "evidencia; se cierra solo con una prueba que lo cubra")],
          anchos=[4.4, 12.4], fs=8.4, titulo="Criterios de entrada y salida del proceso de pruebas",
          resaltar_col0=True)

    # ---- 2.1.6.14 ----
    h2(doc, "2.1.6.14  Herramientas automatizadas y manuales en las pruebas")
    criterio(doc, "2.1.6.14", "Destacado (5 puntos)",
             "Uso balanceado y efectivo de herramientas automatizadas y manuales.")
    evidencia(doc, "Tabla 34 (12 herramientas clasificadas por tipo y momento de ejecución) y la "
                   "descripción del pipeline de integración continua.")

    p(doc, "La automatización y la validación manual no compiten: cubren riesgos distintos. Se "
           "automatiza lo que es determinista y debe repetirse en cada cambio —cálculo de estados, "
           "contratos de API, permisos, consultas—. Se valida manualmente lo que depende de criterio "
           "humano: si el operador entiende el estado de un vistazo, si la interfaz se puede usar con "
           "guantes o si el flujo completo tiene sentido para el supervisor.")

    tabla(doc,
          ["Tipo", "Herramienta", "Uso en el proyecto", "Cuándo se ejecuta"],
          D.HERRAMIENTAS,
          anchos=[2.4, 4.2, 6.2, 4.0], fs=8.2,
          titulo="Herramientas automatizadas y manuales del plan de pruebas", resaltar_col0=True)

    h3(doc, "Pipeline de integración continua")
    pasos = [
        ("1. Integración", "El desarrollador sube la rama y abre un pull request"),
        ("2. Análisis estático", "Ruff, ESLint y Bandit revisan estilo y seguridad"),
        ("3. Pruebas unitarias", "pytest y Vitest ejecutan la base de la pirámide"),
        ("4. Pruebas de integración", "Testcontainers levanta PostgreSQL y se prueban los contratos"),
        ("5. Seguridad de dependencias", "pip-audit y gitleaks; el pipeline falla si hay hallazgos"),
        ("6. Cobertura", "Se publica el porcentaje; por debajo del umbral, el pipeline falla"),
        ("7. Revisión por pares", "Un integrante distinto aprueba el cambio"),
        ("8. Despliegue", "Fusión a main y despliegue automático al entorno de pruebas"),
    ]
    for titulo, detalle in pasos:
        par = doc.add_paragraph(style="List Number")
        r = par.add_run(titulo + ": ")
        r.bold = True
        par.add_run(detalle)

    p(doc, "La decisión de ejecutar las pruebas de rendimiento solo antes de cada entrega —y no en "
           "cada push— es deliberada: son lentas y consumen recursos, y su valor está en detectar "
           "regresiones de escala, no errores de lógica del día a día.")

    # ---- 2.1.6.15 ----
    h2(doc, "2.1.6.15  Preparación para responder las preguntas del profesor")
    criterio(doc, "2.1.6.15", "Destacado (5 puntos)",
             "Responde las preguntas del profesor de manera clara, precisa y con fundamentos sólidos.")
    evidencia(doc, "Tabla 35 (reparto de temas por integrante), Anexo D (20 preguntas con su respuesta "
                   "fundamentada) y la guía de ensayo.")

    p(doc, "La defensa no se improvisa: se preparó un banco de veinte preguntas probables, cada una con "
           "una respuesta breve y con la evidencia documental que la respalda (Anexo D). Además se "
           "definió un reparto de temas, con la regla de que ningún integrante puede ignorar una "
           "decisión estructural aunque no sea suya.")

    tabla(doc,
          ["Integrante", "Temas que debe dominar en profundidad", "Respaldo documental"],
          [("Leonardo Daza", "Metodología, cronograma, priorización, validación con usuarios y "
                             "trazabilidad de requisitos",
            "Capítulo 2.1.1, 2.1.3.7, Anexo C"),
           ("José Sarabia", "Arquitectura 4+1, modelo de datos, seguridad y decisiones técnicas",
            "Capítulos 2.1.2, 2.1.4 y 2.1.5"),
           ("Daniel Paredes", "Prototipo, guía visual, adaptabilidad y plan de pruebas",
            "Capítulos 2.1.3 y 2.1.6, Anexo F")],
          anchos=[3.2, 8.0, 5.6], fs=8.4,
          titulo="Reparto de temas para la defensa", resaltar_col0=True)

    h3(doc, "Estrategia de respuesta")
    bullets(doc, [
        ("Responder con la decisión y después el motivo: ", "«elegimos un monolito modular porque con "
         "tres integrantes la complejidad operativa de los microservicios no se pagaba»."),
        ("Citar la evidencia: ", "toda afirmación se puede señalar en una tabla o figura del informe; "
         "saber la sección es tan importante como saber la respuesta."),
        ("Reconocer el límite: ", "cuando la pregunta exige un dato que la empresa no entregó, la "
         "respuesta correcta es señalar el supuesto académico y explicar cómo se validaría."),
        ("Distinguir diseño de implementación: ", "este informe es el diseño; si preguntan por el "
         "código, corresponde remitirse a ES3 sin confundir el alcance."),
        ("Argumentar las alternativas descartadas: ", "la mayoría de las preguntas difíciles apuntan a "
         "«¿por qué no usaron X?»; las Tablas 4 y 14 tienen la respuesta."),
    ])

    h3(doc, "Ensayo y materiales de demostración")
    p(doc, "Se planificaron dos ensayos completos: uno de contenido, con preguntas cruzadas entre "
           "integrantes, y otro de tiempos, de quince minutos. Para la demostración se preparó una "
           "secuencia guiada sobre el prototipo —operador, supervisor, administrador— que permite "
           "recorrer el flujo completo en menos de cuatro minutos y volver al punto de partida si algo "
           "falla.")


# --------------------------------------------------------------------------- #
# Anexos
# --------------------------------------------------------------------------- #
def anexos(doc):
    salto_pagina(doc)
    h1(doc, "Anexos")

    # ---- A ----
    h2(doc, "Anexo A. Casos de uso expandidos")
    p(doc, "Se detallan los seis escenarios que la arquitectura debe soportar. Cada uno se describe con "
           "su actor, la precondición, el flujo principal y el resultado verificable.")
    for cod, nombre, actor_, pre, flujo, result in D.ESCENARIOS:
        h3(doc, f"{cod} · {nombre}")
        tabla(doc,
              ["Campo", "Descripción"],
              [("Actor", actor_), ("Precondición", pre), ("Flujo principal", flujo),
               ("Resultado verificable", result)],
              anchos=[3.6, 13.2], fs=8.4)

    # ---- B ----
    salto_pagina(doc)
    h2(doc, "Anexo B. Script DDL de PostgreSQL")
    p(doc, "El siguiente script materializa el modelo del capítulo 2.1.4. Se incluye completo para que "
           "la evaluación pueda comprobar que el diseño es implementable y no solo un diagrama.")
    ddl = """-- =====================================================================
-- ES2 · Sistema Web de Monitoreo y Trazabilidad del Trefilado
-- Esquema PostgreSQL 16 (extracto ejecutable del modelo lógico)
-- =====================================================================
CREATE TYPE estado_inspeccion AS ENUM ('aprobado', 'rechazado', 'sin_receta');
CREATE TYPE severidad_alarma AS ENUM ('baja', 'media', 'alta');

CREATE TABLE roles (
    id           SERIAL PRIMARY KEY,
    nombre       VARCHAR(30) NOT NULL UNIQUE,
    descripcion  TEXT
);

CREATE TABLE usuarios (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(40) NOT NULL UNIQUE,
    pin_hash    TEXT        NOT NULL,
    rol_id      INTEGER     NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    activo      BOOLEAN     NOT NULL DEFAULT TRUE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sesiones (
    id           SERIAL PRIMARY KEY,
    usuario_id   INTEGER     NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    refresh_hash TEXT        NOT NULL,
    expira_en    TIMESTAMPTZ NOT NULL,
    revocado     BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE recetas (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(40)   NOT NULL UNIQUE,
    min_tol     NUMERIC(5,2)  NOT NULL,
    max_tol     NUMERIC(5,2)  NOT NULL,
    activa      BOOLEAN       NOT NULL DEFAULT TRUE,
    creado_por  INTEGER       REFERENCES usuarios(id) ON DELETE RESTRICT,
    creado_en   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT chk_tolerancia CHECK (min_tol < max_tol)
);

CREATE TABLE lotes (
    id           SERIAL PRIMARY KEY,
    codigo       VARCHAR(30) NOT NULL UNIQUE,
    receta_id    INTEGER     REFERENCES recetas(id) ON DELETE RESTRICT,
    fecha_inicio DATE        NOT NULL,
    fecha_fin    DATE,
    turno        CHAR(1)     CHECK (turno IN ('A','B','C'))
);

CREATE TABLE batches (
    id          SERIAL PRIMARY KEY,
    lote_id     INTEGER     NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    numero      INTEGER     NOT NULL,
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lote_id, numero)
);

CREATE TABLE inspecciones (
    id          BIGSERIAL PRIMARY KEY,
    fecha_hora  TIMESTAMPTZ      NOT NULL,
    receta_id   INTEGER          REFERENCES recetas(id)  ON DELETE RESTRICT,
    lote_id     INTEGER          REFERENCES lotes(id)    ON DELETE RESTRICT,
    batch_id    INTEGER          REFERENCES batches(id)  ON DELETE RESTRICT,
    operador_id INTEGER          REFERENCES usuarios(id) ON DELETE RESTRICT,
    angulo      NUMERIC(5,2),
    limite_min  NUMERIC(5,2)     NOT NULL,   -- copia histórica (RNF-10)
    limite_max  NUMERIC(5,2)     NOT NULL,
    estado      estado_inspeccion NOT NULL,
    observacion TEXT,
    origen      VARCHAR(20)      NOT NULL DEFAULT 'api',
    creado_en   TIMESTAMPTZ      NOT NULL DEFAULT now(),
    CONSTRAINT chk_angulo CHECK (angulo IS NULL OR angulo BETWEEN 0 AND 180)
);

CREATE TABLE imagenes (
    id            BIGSERIAL PRIMARY KEY,
    inspeccion_id BIGINT      NOT NULL REFERENCES inspecciones(id) ON DELETE CASCADE,
    objeto_key    TEXT        NOT NULL,
    tamano_bytes  BIGINT      NOT NULL,
    sha256        CHAR(64)    NOT NULL,
    capturada_en  TIMESTAMPTZ NOT NULL
);

CREATE TABLE alarmas (
    id            BIGSERIAL PRIMARY KEY,
    inspeccion_id BIGINT            NOT NULL REFERENCES inspecciones(id) ON DELETE CASCADE,
    tipo          VARCHAR(30)       NOT NULL,
    severidad     severidad_alarma  NOT NULL,
    notificada    BOOLEAN           NOT NULL DEFAULT FALSE,
    creada_en     TIMESTAMPTZ       NOT NULL DEFAULT now()
);

CREATE TABLE auditoria (
    id         BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER     REFERENCES usuarios(id) ON DELETE SET NULL,
    accion     VARCHAR(20) NOT NULL,
    entidad    VARCHAR(30) NOT NULL,
    entidad_id BIGINT,
    fecha      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip         INET,
    detalle    JSONB
);

-- Índices (Tabla 22)
CREATE INDEX idx_inspecciones_fecha  ON inspecciones (fecha_hora DESC);
CREATE INDEX idx_inspecciones_lote   ON inspecciones (lote_id, fecha_hora DESC);
CREATE INDEX idx_inspecciones_receta ON inspecciones (receta_id, fecha_hora DESC);
CREATE INDEX idx_inspecciones_estado ON inspecciones (estado)
       WHERE estado <> 'aprobado';
CREATE INDEX idx_alarmas_pendientes  ON alarmas (creada_en)
       WHERE notificada = FALSE;

-- Inmutabilidad del registro (RNF-10): prohibido modificar límites aplicados
CREATE OR REPLACE FUNCTION bloquear_cambio_limites() RETURNS trigger AS $$
BEGIN
    IF NEW.limite_min <> OLD.limite_min OR NEW.limite_max <> OLD.limite_max THEN
        RAISE EXCEPTION 'Los límites aplicados a una inspección son inmutables';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_inspecciones_inmutables
    BEFORE UPDATE ON inspecciones
    FOR EACH ROW EXECUTE FUNCTION bloquear_cambio_limites();"""
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(8)
    r = par.add_run(ddl)
    r.font.name = "Consolas"
    r.font.size = Pt(7.4)
    r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    par.paragraph_format.line_spacing = 1.0

    # ---- C ----
    salto_pagina(doc)
    h2(doc, "Anexo C. Matriz de trazabilidad")
    p(doc, "La matriz permite seguir cada necesidad desde su origen hasta la prueba que la verifica. "
           "Es el instrumento que demuestra coherencia entre el diagnóstico, el diseño y el plan de "
           "pruebas.")
    tabla(doc,
          ["Necesidad", "Historias", "Requisitos", "Casos de uso", "Diseño", "Pruebas"],
          D.TRAZABILIDAD,
          anchos=[3.6, 2.4, 2.8, 2.4, 2.8, 2.8], fs=7.6,
          titulo="Matriz de trazabilidad: necesidad → historia → requisito → caso de uso → diseño → prueba",
          resaltar_col0=True)

    # ---- D ----
    salto_pagina(doc)
    h2(doc, "Anexo D. Preguntas probables de la defensa y respuestas fundamentadas")
    p(doc, "Se documentaron veinte preguntas agrupadas por tema. Cada respuesta remite a la evidencia "
           "que la respalda, de modo que el equipo pueda mostrarla durante la defensa.")
    preguntas = [
        ("Metodología",
         "¿Por qué Scrum y no una metodología tradicional?",
         "Porque el diseño necesitaba validarse con usuarios antes de construir. Scrum permitió "
         "entregar el prototipo v1 en el Sprint 1 y corregirlo con el feedback del Sprint 2 sin "
         "rehacer la arquitectura. Una metodología en cascada habría fijado la interfaz antes de "
         "conocer la opinión de los operadores."),
        ("Metodología",
         "¿Qué pasa si un sprint no se cumple?",
         "La red de dependencias identifica qué actividades tienen holgura. Las que están en la ruta "
         "crítica —levantamiento, arquitectura, modelo de datos, plan de pruebas e informe— no pueden "
         "retrasarse sin mover la entrega; por eso se priorizan y se revisan en cada daily. Las demás "
         "tienen entre dos y cuatro días de margen documentados en la Tabla 8."),
        ("Metodología",
         "¿Cómo priorizaron el backlog?",
         "Con MoSCoW cruzado con una matriz de valor y esfuerzo. Las nueve historias Must sostienen el "
         "flujo mínimo del desafío; las Should aportan valor al supervisor; las Could son mejoras; y "
         "la integración con el ERP corporativo queda fuera de alcance porque depende de sistemas que no "
         "controlamos; ninguna de las 14 historias del ES1 queda fuera del backlog."),
        ("Arquitectura", "¿Por qué no microservicios?",
         "Porque el costo operativo no se justifica con tres integrantes. Los microservicios exigen "
         "orquestación, comunicación entre servicios, trazabilidad distribuida y versionado de "
         "contratos; ese esfuerzo habría consumido el tiempo disponible para resolver el problema del "
         "negocio. El monolito modular conserva fronteras claras y permite extraer un módulo si el "
         "volumen lo exige más adelante."),
        ("Arquitectura", "¿Qué vista del 4+1 les costó más y por qué?",
         "La de procesos. Obligó a decidir qué operaciones son transaccionales y cuáles pueden ser "
         "asíncronas. La conclusión fue que el registro de la inspección debe ser una transacción "
         "única —leer la receta y escribir el hecho—, mientras que el envío de alertas por correo "
         "puede salir del ciclo de la petición sin afectar la integridad del dato."),
        ("Arquitectura", "¿Cómo escala la solución si las inspecciones se multiplican por diez?",
         "La API y el trabajador no guardan estado, así que se replican horizontalmente detrás del "
         "proxy. En la base de datos, los índices parciales y la paginación por cursor sostienen las "
         "consultas; el histórico antiguo se puede archivar sin borrar trazabilidad. La primera "
         "restricción aparecería en el almacenamiento de imágenes, que se resuelve con políticas de "
         "retención."),
        ("Datos", "¿Por qué guardan los límites en la inspección si ya están en la receta?",
         "Porque la trazabilidad exige que el registro conserve las condiciones en que fue evaluado. "
         "Si la tolerancia de una receta cambia, el histórico no debe reinterpretarse: una pieza "
         "rechazada en septiembre no puede volverse aprobada en octubre por un cambio de "
         "configuración. Es una desnormalización deliberada, documentada en la Tabla 21."),
        ("Datos", "¿El modelo está en tercera forma normal?",
         "Sí, con una excepción justificada: la copia de los límites en la entidad «inspecciones». "
         "Además la columna «detalle» de auditoría usa JSONB, que no es una violación de 3FN sino el "
         "uso de un tipo semiestructurado para datos heterogéneos."),
        ("Datos", "¿Por qué las imágenes no están en la base de datos?",
         "Porque son archivos binarios grandes que multiplicarían el tamaño de los respaldos y "
         "degradarían las consultas. Se guardan en almacenamiento de objetos y en la base queda la "
         "referencia con el checksum, que permite verificar integridad sin cargar el archivo."),
        ("Datos", "¿Qué pasa si se pierde una imagen?",
         "El checksum registrado en la tabla «imagenes» permite detectar la discrepancia. El sistema "
         "marca la inspección como incompleta, pero conserva la medición y su trazabilidad, que es el "
         "dato crítico para calidad."),
        ("Seguridad", "¿Por qué Argon2id y no SHA-256?",
         "Porque SHA-256 es rápido, y esa velocidad favorece al atacante que prueba millones de "
         "combinaciones. Argon2id es deliberadamente costoso en memoria y tiempo, lo que hace inviable "
         "un ataque de fuerza bruta sobre PIN de seis dígitos, incluso con GPUs."),
        ("Seguridad", "¿Cómo evitan que un operador vea datos que no le corresponden?",
         "Con dos controles: la verificación de rol en el servidor en cada endpoint (Tabla 27) y el "
         "filtrado por alcance en la consulta, de modo que el operador solo accede al turno actual. El "
         "cliente nunca decide permisos: aunque se manipule el navegador, la API responde 403."),
        ("Seguridad", "¿Qué amenaza consideran más grave?",
         "La manipulación de una medición para forzar un aprobado, porque ataca la razón de ser del "
         "sistema. Se mitiga con inmutabilidad del registro a nivel de base de datos (trigger), "
         "auditoría con valores anteriores y posteriores, y separación de roles."),
        ("Seguridad", "¿Dónde guardan las credenciales de la base de datos?",
         "En variables de entorno del contenedor, nunca en el repositorio. El pipeline ejecuta gitleaks "
         "y falla si detecta un secreto; además el archivo de ejemplo del repositorio solo contiene "
         "valores ficticios."),
        ("Prototipo", "¿El prototipo es funcional o solo un mockup?",
         "Es funcional: es una aplicación HTML, CSS y JavaScript que se abre en el navegador, permite "
         "navegar entre las seis pantallas y filtrar la tabla del histórico. No tiene backend, pero "
         "cada interacción clave está representada y se puede comprobar la adaptabilidad redimensionando "
         "la ventana."),
        ("Prototipo", "¿Cómo garantizan la accesibilidad?",
         "Con contraste mínimo AA verificado (Tabla 17), foco visible en todos los controles, etiquetas "
         "asociadas a los campos, estado comunicado con texto y no solo con color, y respeto por la "
         "preferencia de movimiento reducido."),
        ("Pruebas", "¿Qué pruebas no van a alcanzar a hacer?",
         "Las de penetración formales y las de disponibilidad prolongada: requieren tiempo de "
         "observación y herramientas especializadas. Se cubren parcialmente con pruebas de seguridad "
         "automatizadas (TP-17, TP-18) y con monitoreo, y se declaran como deuda pendiente para la "
         "operación real."),
        ("Pruebas", "¿Cómo miden el rendimiento sin datos reales?",
         "Con un supuesto académico declarado: 100 000 inspecciones y 50 usuarios concurrentes "
         "(Anexo E). Los umbrales se verifican con k6 y EXPLAIN ANALYZE sobre una base sembrada con ese "
         "volumen, de modo que el resultado sea reproducible y ajustable cuando existan cifras reales."),
        ("Gestión", "¿Qué entregable demuestra que el diseño fue validado?",
         "La Tabla 19: once observaciones registradas con participante, decisión de diseño y cambio "
         "aplicado. Nueve se incorporaron en la versión 2 del prototipo y dos quedaron en revisión, lo "
         "que muestra que el proceso no fue un trámite sino una revisión con efectos verificables."),
        ("Gestión", "¿Qué harían distinto si tuvieran otro semestre?",
         "Adelantaríamos la validación con usuarios reales de planta, que fue el supuesto más débil: "
         "trabajamos con el docente contraparte y con perfiles simulados. También automatizaríamos las "
         "pruebas de rendimiento desde el inicio, para detectar antes los problemas de consulta."),
    ]
    actual = None
    for tema, pregunta, respuesta in preguntas:
        if tema != actual:
            h3(doc, tema)
            actual = tema
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(6)
        r = par.add_run("P. " + pregunta)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = VERDE_CLARO
        par2 = doc.add_paragraph()
        r2 = par2.add_run("R. " + respuesta)
        r2.font.size = Pt(9.5)

    # ---- E ----
    salto_pagina(doc)
    h2(doc, "Anexo E. Supuestos académicos y glosario")
    p(doc, "El documento de la empresa advierte explícitamente que la frecuencia y el volumen de "
           "registros no deben inventarse. Por eso todos los valores de dimensionamiento se declaran "
           "aquí como supuestos académicos, no como datos de producción de Aceros AZA.")
    tabla(doc,
          ["Tema", "Supuesto declarado", "Origen y cómo se validaría"],
          D.SUPUESTOS,
          anchos=[3.2, 5.6, 8.0], fs=8.2,
          titulo="Supuestos académicos de dimensionamiento", resaltar_col0=True)

    h3(doc, "Glosario")
    tabla(doc,
          ["Término", "Definición en el contexto del proyecto"],
          [("Ráfaga / trigger", "Conjunto de imágenes capturadas por una señal externa (flanco en "
                                "Line0) que corresponde a una inspección"),
           ("Ángulo de salida", "Medición angular que el sistema de visión obtiene del material al "
                                "salir del proceso"),
           ("Receta", "Configuración de un producto: nombre y tolerancias mínima y máxima del ángulo"),
           ("Lote", "Agrupación de producción a la que se asocian varias inspecciones"),
           ("Batch", "Subdivisión del lote que agrupa un conjunto acotado de inspecciones"),
           ("Trazabilidad", "Capacidad de reconstruir qué se midió, cuándo, con qué receta y por quién, "
                            "sin que el registro pueda alterarse"),
           ("RBAC", "Control de acceso basado en roles: los permisos se asignan al rol, no a la persona"),
           ("JWT", "Token firmado que acredita la identidad del usuario durante un período corto"),
           ("MoSCoW", "Técnica de priorización: Must, Should, Could, Won't have"),
           ("Vistas 4+1", "Marco de Kruchten para describir arquitectura desde cinco perspectivas"),
           ("Definition of Done", "Criterios que debe cumplir una historia para considerarse terminada")],
          anchos=[3.6, 13.2], fs=8.4, titulo="Glosario de términos", resaltar_col0=True)

    # ---- F ----
    salto_pagina(doc)
    h2(doc, "Anexo F. Inventario de evidencias y archivos entregados")
    p(doc, "Junto con este informe se entregan los artefactos que permiten verificar cada afirmación "
           "sin depender del texto.")
    tabla(doc,
          ["Archivo o carpeta", "Contenido", "Criterios que respalda"],
          [("Informe_ES2_AZA.docx", "Este informe", "2.1.1.1 a 2.1.6.15"),
           ("prototipo/aza-prototipo.html", "Prototipo interactivo navegable y responsive",
            "2.1.3.5, 2.1.3.6, 2.1.3.7"),
           ("diagramas/01 a 13", "Diagramas editables del informe (cronograma, red, 4+1, DER, "
                                 "seguridad, pruebas)", "2.1.1 a 2.1.6"),
           ("diagramas/14 a 23", "Capturas del prototipo en escritorio, tablet y móvil",
            "2.1.3.5, 2.1.3.6"),
           ("Anexo B (en el informe)", "Script DDL ejecutable del modelo de datos", "2.1.4.8, 2.1.4.9"),
           ("Anexo C (en el informe)", "Matriz de trazabilidad completa", "Transversal"),
           ("Anexo D (en el informe)", "Banco de preguntas de defensa con respuestas", "2.1.6.15"),
           ("Anexo G (en el informe)", "Catálogo de necesidades, RF, RNF y relación HU→RF del ES1",
            "Transversal")],
          anchos=[4.4, 8.0, 4.4], fs=8.4,
          titulo="Inventario de archivos entregados y criterios que respaldan", resaltar_col0=True)

    # ---- G ----
    salto_pagina(doc)
    h2(doc, "Anexo G. Catálogo de requisitos heredados del ES1")
    p(doc, "Para que la evaluación pueda verificar la trazabilidad sin abrir un segundo archivo, este "
           "anexo reproduce el catálogo del informe ES1 conservando su numeración original: las diez "
           "necesidades de negocio, los doce requerimientos funcionales, los doce requerimientos no "
           "funcionales y la relación de cada historia de usuario con los requisitos que la "
           "implementan. El diseño descrito en este informe no agrega ni elimina requisitos: los "
           "refina y los hace implementables.")

    tabla(doc,
          ["ID", "Necesidad de negocio", "Actores que la manifiestan", "Prioridad", "Problemas de origen"],
          D.NECESIDADES,
          anchos=[1.3, 7.4, 3.6, 1.6, 2.9], fs=8.2,
          titulo="Necesidades de negocio heredadas del ES1", resaltar_col0=True)

    tabla(doc,
          ["ID", "Requerimiento funcional", "Categoría", "Historias asociadas"],
          D.RF,
          anchos=[1.3, 9.2, 3.3, 3.0], fs=8.2,
          titulo="Requerimientos funcionales del ES1", resaltar_col0=True)

    tabla(doc,
          ["ID", "Requerimiento no funcional", "Criterio de aceptación del ES1", "Trazabilidad"],
          [(r[0], r[1], r[2], r[3]) for r in D.RNF],
          anchos=[1.5, 3.2, 8.4, 3.7], fs=8.2,
          titulo="Requerimientos no funcionales del ES1", resaltar_col0=True)

    tabla(doc,
          ["Historia", "Actor", "Prioridad MoSCoW", "Requisitos que la implementan"],
          [(h[0], h[2], h[5], {
              "HU-OP-01": "RF-02, RF-03, RF-07",
              "HU-OP-02": "RF-04",
              "HU-OP-03": "RF-07",
              "HU-SU-01": "RF-03",
              "HU-SU-02": "RF-04, RF-09",
              "HU-SU-03": "RF-02, RF-12",
              "HU-SU-04": "RF-08",
              "HU-AD-01": "RF-05, RF-11",
              "HU-AD-02": "RF-06",
              "HU-AD-03": "RF-06",
              "HU-AD-04": "RF-07",
              "HU-SC-01": "RF-01, RF-02",
              "HU-SC-02": "RF-01",
              "HU-CA-01": "RF-04, RF-08, RF-09",
          }[h[0]]) for h in D.HU],
          anchos=[2.0, 4.4, 3.2, 7.2], fs=8.2,
          titulo="Relación entre historias de usuario, prioridad y requerimientos",
          resaltar_col0=True)

    h3(doc, "Conclusión del diseño")
    p(doc, "El diseño presentado es coherente con el problema planteado: un sistema que recibe una "
           "medición ya calculada, la valida, la persiste de forma inmutable y la devuelve como "
           "información útil para tres perfiles distintos. Las decisiones estructurales —monolito "
           "modular, PostgreSQL con almacenamiento de objetos, RBAC verificado en el servidor y "
           "desnormalización controlada de los límites— se eligieron por el contexto del proyecto y no "
           "por preferencia tecnológica, y cada una tiene una consecuencia asumida y documentada.")
    p(doc, "Queda identificado el principal límite de este trabajo: la validación se realizó con "
           "perfiles simulados y con el docente contraparte, no con operadores reales de planta, y los "
           "volúmenes de carga son supuestos académicos. Ambos aspectos están declarados y son "
           "revisables cuando la contraparte entregue los datos que el propio desafío señala como "
           "pendientes.")


# --------------------------------------------------------------------------- #
def anexo_h_matriz(doc):
    h2(doc, "Anexo H. Matriz de evaluación cuantitativa de metodologías")
    p(doc, "La Tabla 4 resume el puntaje final de cada alternativa. Este anexo muestra la matriz "
           "completa para que la evaluación pueda reproducirse: seis criterios ponderados, cinco "
           "alternativas y una escala de 1 (no cumple) a 5 (cumple plenamente). El promedio ponderado "
           "se obtiene multiplicando cada puntaje por el peso del criterio y sumando los seis "
           "resultados.")

    tabla(doc,
          ["Criterio (peso)", "Cascada", "Kanban", "RUP puro", "Scrum + XP", "Scrum + 4+1"],
          [("Adaptabilidad al cambio (25 %)", "1", "5", "2", "4", "5"),
           ("Documentación arquitectónica (20 %)", "4", "1", "5", "2", "5"),
           ("Ajuste a equipo de 3 personas (15 %)", "2", "4", "2", "3", "4"),
           ("Entregas frecuentes y validación temprana (15 %)", "1", "4", "2", "4", "5"),
           ("Trazabilidad requisito → prueba (15 %)", "4", "2", "5", "3", "4"),
           ("Curva de aprendizaje en el plazo (10 %)", "5", "4", "2", "2", "3"),
           ("Promedio ponderado (0–5)", "2,60", "3,35", "3,05", "3,10", "4,50")],
          anchos=[5.4, 2.1, 2.1, 2.2, 2.3, 2.7], fs=8.6,
          titulo="Matriz de evaluación de metodologías: puntaje por criterio y promedio ponderado",
          resaltar_col0=True)

    p(doc, "Los supuestos de la puntuación son explícitos: la escala es ordinal y los pesos reflejan la "
           "importancia de cada criterio para este proyecto en particular, no un valor universal. Un "
           "equipo de diez personas con un cliente que cambia requisitos todas las semanas obtendría "
           "pesos distintos y, probablemente, un ganador distinto.")

    h3(doc, "Lectura del resultado")
    p(doc, "La diferencia entre la opción adoptada (4,50) y la segunda (Kanban, 3,35) no proviene de "
           "la adaptabilidad —donde ambas obtienen el máximo— sino de la documentación arquitectónica y "
           "de los puntos de cierre: el proyecto se evalúa en cuatro hitos con fecha fija y la rúbrica "
           "exige justificar la arquitectura con cinco vistas (Kruchten, 1995). Kanban no impone esos "
           "cierres por diseño (Anderson, 2010).")
    p(doc, "Cascada obtiene el puntaje más bajo por una razón concreta y no por antigüedad: su modelo "
           "fija la interfaz y los requisitos antes de validarlos, lo que choca con el hallazgo del "
           "ES1, donde el prototipo debió corregirse tras la validación con usuarios.")


def referencias(doc):
    salto_pagina(doc)
    h1(doc, "Referencias bibliográficas")
    p(doc, "Todas las fuentes citadas en el informe se presentan a continuación en formato APA 7, "
           "ordenadas alfabéticamente. Las citas dentro del texto usan el formato autor–año.")

    refs = [
        ("Anderson, D. J. (2010). ", "Kanban: Successful evolutionary change for your technology "
                                     "business", ". Blue Hole Press."),
        ("Beck, K. (2002). ", "Test-driven development: By example", ". Addison-Wesley."),
        ("Few, S. (2006). ", "Information dashboard design: The effective visual communication of "
                             "data", ". O'Reilly Media."),
        ("Fielding, R. T. (2000). ", "Architectural styles and the design of network-based software "
                                     "architectures", " (Tesis doctoral, University of California, "
                                     "Irvine)."),
        ("Fowler, M. (2002). ", "Patterns of enterprise application architecture", ". Addison-Wesley."),
        ("Kagermann, H., Wahlster, W., & Helbig, J. (2013). ", "Recommendations for implementing the "
                                                               "strategic initiative INDUSTRIE 4.0",
         ". acatech."),
        ("Kleppmann, M. (2017). ", "Designing data-intensive applications", ". O'Reilly Media."),
        ("Knaflic, C. N. (2015). ", "Storytelling with data: A data visualization guide for business "
                                    "professionals", ". Wiley."),
        ("Kruchten, P. (1995). The 4+1 view model of architecture. ", "IEEE Software, 12",
         "(6), 42–50. https://doi.org/10.1109/52.469759"),
        ("Lasi, H., Fettke, P., Kemper, H.-G., Feld, T., & Hoffmann, M. (2014). Industry 4.0. ",
         "Business & Information Systems Engineering, 6",
         "(4), 239–242. https://doi.org/10.1007/s12599-014-0334-4"),
        ("McGraw, G. (2006). ", "Software security: Building security in", ". Addison-Wesley."),
        ("Myers, G. J., Sandler, C., & Badgett, T. (2011). ", "The art of software testing",
         " (3.ª ed.). Wiley."),
        ("National Institute of Standards and Technology. (2020). ", "Digital identity guidelines",
         " (NIST SP 800-63-3). U.S. Department of Commerce. "
         "https://doi.org/10.6028/NIST.SP.800-63-3"),
        ("OWASP Foundation. (2021). ", "OWASP Top 10:2021", ". https://owasp.org/Top10/"),
        ("Pressman, R. S., & Maxim, B. R. (2020). ", "Software engineering: A practitioner's approach",
         " (9.ª ed.). McGraw-Hill."),
        ("Richardson, L., & Ruby, S. (2007). ", "RESTful web services", ". O'Reilly Media."),
        ("Sandhu, R. S., Coyne, E. J., Feinstein, H. L., & Youman, C. E. (1996). Role-based access "
         "control models. ", "Computer, 29", "(2), 38–47. https://doi.org/10.1109/2.485845"),
        ("Schwab, K. (2017). ", "The fourth industrial revolution", ". Crown Business."),
        ("Schwaber, K., & Sutherland, J. (2020). ", "The Scrum Guide", ". https://scrumguides.org"),
        ("Shneiderman, B. (1996). The eyes have it: A task by data type taxonomy for information "
         "visualizations. En ", "Proceedings of the IEEE Symposium on Visual Languages",
         " (pp. 336–343). IEEE. https://doi.org/10.1109/VL.1996.545307"),
        ("Sommerville, I. (2016). ", "Software engineering", " (10.ª ed.). Pearson."),
        ("World Wide Web Consortium. (2018). ", "Web Content Accessibility Guidelines (WCAG) 2.1",
         ". https://www.w3.org/TR/WCAG21/"),
    ]

    for prefijo, cursiva, sufijo in refs:
        par = doc.add_paragraph()
        par.paragraph_format.left_indent = Cm(1.0)
        par.paragraph_format.first_line_indent = Cm(-1.0)
        par.paragraph_format.space_after = Pt(6)
        par.paragraph_format.line_spacing = 1.05
        par.add_run(prefijo).font.size = Pt(9.5)
        r = par.add_run(cursiva)
        r.italic = True
        r.font.size = Pt(9.5)
        par.add_run(sufijo).font.size = Pt(9.5)


def main():
    doc = Document()
    configurar_estilos(doc)
    configurar_pagina(doc)
    agregar_encabezado_pie(doc)

    portada(doc)
    ficha_documento(doc)
    marco_referencia(doc)
    seccion_211(doc)
    seccion_212(doc)
    seccion_213(doc)
    seccion_214(doc)
    seccion_215(doc)
    seccion_216(doc)
    anexos(doc)
    anexo_h_matriz(doc)
    referencias(doc)

    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")
    print(f"Figuras: {_n_fig[0]} | Tablas: {_n_tab[0]}")
    print(f"Tamaño: {os.path.getsize(SALIDA) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
