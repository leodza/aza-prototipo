# -*- coding: utf-8 -*-
"""Genera el documento de instrucciones y contexto del paquete del proyecto."""
import os
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(RAIZ, "App-Funcional", "evidencias")
SALIDA = os.path.join(RAIZ, "documentos", "INSTRUCCIONES-Y-CONTEXTO.docx")

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


def numeros(items):
    for it in items:
        par = doc.add_paragraph(style="List Number")
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
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


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


def figura(nombre, leyenda, ancho=15.0):
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
run = pie_pag.add_run("Instrucciones y contexto · AZA Analyzer · Aceros AZA ")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(0x78, 0x90, 0x9C)
campo = OxmlElement("w:fldSimple")
campo.set(qn("w:instr"), "PAGE")
pie_pag._p.append(campo)

# ============================================================== PORTADA =====
p("PROYECTO INTEGRADO · INACAP SANTIAGO CENTRO", size=9, bold=True,
  color=RGBColor(0x60, 0x7D, 0x8B), antes=60, despues=2)
p("Instrucciones y contexto", size=27, bold=True, color=VERDE, antes=8, despues=0)
p("del proyecto", size=27, bold=True, color=VERDE, despues=10)
p("Cómo instalarlo en otro computador y en qué estado quedó todo", size=13,
  color=RGBColor(0x33, 0x4A, 0x3A), despues=26)

tabla(["Dato", "Detalle"],
      [["Proyecto", "Sistema Web de Monitoreo y Trazabilidad del Trefilado"],
       ["Cliente", "Aceros AZA · Robotic Systems Chile"],
       ["Equipo", "Leonardo Daza (Product Owner)\nJosé Sarabia (Scrum Master · backend)\nDaniel Paredes (frontend · QA)"],
       ["Docente", "Armin Vladimir Brun Rüth"],
       ["Estado", "Prototipo funcional desplegado en AWS · ES3"],
       ["Fecha", "21 de noviembre de 2026"]],
      anchos=[4.0, 12.2], fuente=9.5)

nota("Este documento acompaña al paquete comprimido del proyecto. Explica cómo ponerlo "
     "a funcionar en un computador nuevo, cómo se usa, y en qué estado quedó cada parte "
     "para poder retomarlo sin perderse.", "Cómo leerlo")

salto()

# ============================================================== 1 ============
doc.add_heading("1. Qué contiene el paquete", level=1)
p("Al descomprimir el archivo quedan estas carpetas. Cada una cumple un papel distinto y "
  "conviene no moverlas entre sí, porque los archivos se buscan por ruta relativa.", align="j")
tabla(["Carpeta", "Qué hay dentro", "¿Se necesita para ejecutar?"],
      [["App-Funcional", "El prototipo: API, interfaz, simulador, pruebas, evidencias y documentos", "Sí, es el programa"],
       ["APP-AZA", "Aplicación de planta original (de aquí sale el motor de visión)", "No: ya está copiado dentro de App-Funcional/vision_aza"],
       ["ES2-Informe", "Informe ES2 completo con sus diagramas (DOCX y figuras)", "No"],
       ["documentos", "Manual de uso, arquitectura de datos y este documento", "No"],
       ["main.cpp", "Firmware del indicador físico (Arduino)", "No"],
       ["README.md", "Resumen del proyecto y enlaces", "No"]],
      anchos=[3.4, 8.0, 5.0], fuente=8.5)

p("Dentro de App-Funcional, lo importante es:", align="j")
tabla(["Elemento", "Para qué"],
      [["INSTALAR.bat", "Crea el entorno de Python e instala las librerías (solo la primera vez)"],
       ["INICIAR.bat", "Levanta el servidor local y abre el navegador"],
       ["NUBE.bat", "Abre el sistema que está desplegado en AWS"],
       ["REINICIAR-DATOS.bat", "Deja la base local como recién instalada"],
       ["app/", "Código del servidor: modelo de datos, API, seguridad y simulador"],
       ["web/", "La interfaz (HTML, CSS y JavaScript, sin compilación)"],
       ["vision_aza/", "Copia del motor de visión de la planta, para que funcione sin depender de APP-AZA"],
       ["tests/", "Las 28 pruebas automatizadas"],
       ["evidencias/", "24 capturas reales del sistema (interfaz, base de datos, S3 y commits)"],
       ["deploy/", "Script para crear la instancia en AWS, la llave y la IP del servidor"]],
      anchos=[4.6, 11.8], fuente=8.5)

# ============================================================== 2 ============
doc.add_heading("2. Instalarlo en un computador nuevo", level=1)
p("Solo hay que hacerlo la primera vez. Después se abre con doble clic, como cualquier "
  "programa.", align="j")

doc.add_heading("2.1 Requisitos", level=2)
vinetas([
    "Windows 10 u 11.",
    "Python 3.12 o superior (con la casilla «Add python.exe to PATH» marcada al instalar).",
    "Conexión a internet la primera vez, para descargar las librerías.",
    "Unos 600 MB libres en disco.",
])

doc.add_heading("2.2 Pasos", level=2)
numeros([
    ("Descomprimir el archivo ", "en una carpeta propia, por ejemplo en el Escritorio. No ejecutarlo desde dentro del ZIP."),
    ("Entrar a la carpeta App-Funcional.", ""),
    ("Doble clic en INSTALAR.bat. ", "Crea un entorno de Python solo para el proyecto e instala las librerías. Tarda entre 3 y 6 minutos y muestra el avance en pantalla."),
    ("Cuando termine, doble clic en INICIAR.bat. ", "Se abre el navegador en http://127.0.0.1:8000 con el sistema funcionando."),
    ("Para detenerlo, ", "cerrar la ventana negra o presionar Ctrl + C."),
])

nota("Si Windows muestra un aviso de SmartScreen al abrir los .bat, elegir «Más información» "
     "y luego «Ejecutar de todas formas». Son archivos de texto, se pueden abrir con el "
     "Bloc de notas para revisarlos.", "Si Windows se queja")

doc.add_heading("2.3 Qué pasa la primera vez", level=2)
p("Al arrancar, la aplicación crea la base de datos local y la llena con datos de "
  "demostración: 4 usuarios, 7 materiales, 6 recetas, 6 lotes con sus 18 batches y 46 "
  "inspecciones repartidas en el día. No hay que configurar nada.", align="j")
p("En modo local las imágenes se guardan en la carpeta App-Funcional/data/capturas. En la "
  "nube se guardan en Amazon S3, como se explica en el documento de arquitectura.", align="j")

# ============================================================== 3 ============
doc.add_heading("3. Cómo se usa", level=1)
tabla(["Pantalla", "Qué se hace"],
      [["Login", "Se entra con usuario y PIN. ldaza (operador), jsarabia (supervisor), dparedes (administrador). PIN 1234."],
       ["Dashboard", "Resumen del turno: cuántas inspecciones, aprobadas y rechazadas, y la última medición."],
       ["Simulador", "Se elige la receta, la condición y la velocidad del tren, y se dispara una ráfaga de 16 imágenes."],
       ["Histórico", "Se filtra por fecha, receta, lote y estado; se ordena por lote/batch y se exporta a CSV."],
       ["Detalle", "Imagen del diagnóstico, trazabilidad técnica y bitácora del registro."],
       ["Recetas", "Tolerancias y materiales. Solo el administrador puede crear."],
       ["Usuarios", "Alta, activación y baja lógica. Solo el administrador."],
       ["Auditoría", "Quién hizo qué y cuándo."]],
      anchos=[3.2, 13.2], fuente=8.5)
figura("21_nube_dashboard.png", "El panel principal con datos reales del sistema desplegado.")

nota("El detalle completo de cada pantalla, con consultas SQL de ejemplo, está en el "
     "documento «Manual_de_Uso_AZA.docx» que acompaña al proyecto.", "Para profundizar")

# ============================================================== 4 ============
doc.add_heading("4. Conectarse al sistema en la nube", level=1)
p("El sistema también está desplegado en AWS y se usa sin instalar nada, solo con el "
  "navegador.", align="j")
codigo("""NUBE.bat            abre la aplicación y el visor de la base de datos

App     http://13.223.49.56:8000   ldaza / jsarabia / dparedes · PIN 1234
Base    http://13.223.49.56:8081   usuario aza · clave AzaLab2026Db""", "Acceso")
p("La dirección se lee del archivo deploy/ip.txt, que se actualiza solo cada vez que se "
  "despliega. Si el servidor no responde, NUBE.bat lo avisa y explica qué hacer.", align="j")
nota("El entorno vive en un laboratorio de AWS Academy. Cuando la sesión del curso termina, "
     "la instancia se apaga y puede recibir otra dirección. Para volver a levantarla están "
     "los tres comandos de la guía de despliegue (App-Funcional/GUIA-AWS.md).", "Importante")

# ============================================================== 5 ============
doc.add_heading("5. Contexto: qué se construyó", level=1)
p("Esta sección sirve para retomar el trabajo sin tener que reconstruir la historia.", align="j")

doc.add_heading("5.1 El prototipo", level=2)
vinetas([
    ("Backend: ", "FastAPI con SQLAlchemy. Registra inspecciones, expone 29 rutas REST y aplica permisos por rol en el servidor."),
    ("Interfaz: ", "HTML, CSS y JavaScript sin compilación. El menú se arma según el rol y cada vista se adapta."),
    ("Simulador: ", "Genera 16 imágenes BMP y las analiza con el mismo motor de visión de la planta, incluido en vision_aza/."),
    ("Datos: ", "PostgreSQL en la nube (10 tablas) y Amazon S3 para las imágenes de cada ráfaga."),
    ("Pruebas: ", "28 pruebas automatizadas de API, permisos y simulador."),
])

doc.add_heading("5.2 Los cambios pedidos en la reunión", level=2)
p("En la reunión con Robotic Systems Chile se pidieron seis ajustes, y los seis están "
  "implementados:", align="j")
tabla(["#", "Pedido", "Cómo quedó"],
      [["1", "Asociar las ID con recetas y batches", "Cada registro muestra «A-36 #1» y «L-2026-0410 · B1 #1»"],
       ["2", "Ordenar primero lote y después batch", "Selector de orden en el histórico, con lote → batch por defecto"],
       ["3", "Fecha con año primero", "Formato 2026-11-21 20:26:55 en todo el sistema"],
       ["4", "Tipos de materiales, no solo acero", "Catálogo con acero, cobre, latón, aluminio y bronce; cada receta tiene su material"],
       ["5", "Acelerar o desacelerar el proceso", "Control de 4 a 30 m/min; 2,8° de variación por m/min"],
       ["6", "Opción aleatoria", "Tercera condición del simulador: puede salir bien o mal"]],
      anchos=[0.9, 5.6, 9.9], fuente=8.5)

doc.add_heading("5.3 Decisiones técnicas y por qué", level=2)
tabla(["Decisión", "Motivo"],
      [["PostgreSQL para los registros", "Relaciones, transacciones e integridad; el informe ya lo declaraba"],
       ["JSONB en la bitácora", "Cada entidad guarda valores distintos; así lo pedía el diccionario de datos del ES2"],
       ["Amazon S3 para las imágenes", "15 MB por ráfaga; se accede por clave y cuesta centavos al mes"],
       ["Rutas del bucket por lote y batch", "La trazabilidad se ve también en el almacenamiento, no solo en la base"],
       ["Borrado de la copia local", "Los datos quedan solo en la nube; el servidor no acumula imágenes"],
       ["S3 en lugar de MinIO", "MinIO dejó de distribuir su versión libre; el protocolo es el mismo y el código no cambió"]],
      anchos=[5.4, 11.0], fuente=8.5)

# ============================================================== 6 ============
doc.add_heading("6. Dónde está cada cosa", level=1)
codigo("""Proyecto/
  README.md                     resumen y enlaces
  INSTRUCCIONES-Y-CONTEXTO.docx este documento
  main.cpp                      firmware del indicador

  App-Funcional/
    INSTALAR.bat                entorno de Python (solo la 1a vez)
    INICIAR.bat                 arranca en local
    NUBE.bat                    abre el sistema en AWS
    app/                        db.py  main.py  seguridad.py  simulador.py  almacenamiento.py
    web/                        index.html  styles.css  app.js
    vision_aza/                 motor de visión (copia de APP-AZA)
    tests/test_api.py           28 pruebas
    evidencias/                 24 capturas
    deploy/                     desplegar_aws.py  ip.txt  guardar-ip.bat  GUIA-AWS.md
    documentos internos         README.md  GUIA-AWS.md

  APP-AZA/                      aplicación de planta original
  ES2-Informe/                  informe ES2 y sus diagramas
  documentos/                   manual de uso y arquitectura de datos""", "Mapa del paquete")

# ============================================================== 7 ============
doc.add_heading("7. Estado del proyecto y qué falta", level=1)
tabla(["Parte", "Estado"],
      [["Prototipo funcional (local y en la nube)", "Terminado y probado"],
       ["Base de datos PostgreSQL con las 10 tablas", "Terminada, con datos reales"],
       ["Almacenamiento de imágenes en S3 por lote", "Terminado"],
       ["Seguridad (PIN cifrado, JWT, roles, auditoría)", "Terminada"],
       ["Repositorio con historial de commits", "Publicado en github.com/leodza/aza-prototipo"],
       ["Manual de uso y documento de arquitectura", "Terminados"],
       ["Informe de pruebas para la ES3 (23-11)", "Pendiente: rendimiento y UAT con números"],
       ["Redis + Celery (alertas por correo)", "Pendiente: el flujo actual es síncrono"],
       ["HTTPS con dominio propio", "Pendiente: hoy funciona por HTTP"]],
      anchos=[8.6, 7.8], fuente=8.5)

doc.add_heading("7.1 Lo siguiente, en orden", level=2)
numeros([
    ("Informe de pruebas ES3. ", "Medir tiempos por endpoint, ráfagas por minuto, latencia de la base y casos de aceptación con el usuario."),
    ("Cerrar el acceso. ", "Cambiar los PIN de demostración y, si se publica fuera del laboratorio, agregar HTTPS."),
    ("Alertas por correo. ", "Es la razón por la que el diseño incluye Redis y Celery."),
])

# ============================================================== 8 ============
doc.add_heading("8. Problemas frecuentes", level=1)
tabla(["Síntoma", "Causa", "Solución"],
      [["«No encuentro Python» al instalar", "Python no está instalado o no está en el PATH", "Instalar Python y marcar «Add python.exe to PATH»"],
       ["Los .bat se cierran solos", "Falta el entorno", "Ejecutar INSTALAR.bat primero"],
       ["«ModuleNotFoundError»", "El entorno se creó incompleto", "Borrar la carpeta .venv y volver a ejecutar INSTALAR.bat"],
       ["El puerto 8000 está ocupado", "Hay otra instancia del servidor abierta", "Cerrar la otra ventana o reiniciar el equipo"],
       ["NUBE.bat dice que no responde", "El laboratorio de AWS se apagó o cambió la IP", "Revisar la IP en la consola de AWS y guardarla con deploy\\guardar-ip.bat"],
       ["El login dice «cuenta bloqueada»", "Cinco intentos fallidos", "Esperar 15 minutos"]],
      anchos=[4.6, 5.4, 6.4], fuente=8.5)

doc.add_heading("9. Credenciales y enlaces", level=1)
tabla(["Recurso", "Dato"],
      [["Aplicación (nube)", "http://13.223.49.56:8000"],
       ["Base de datos (visor)", "http://13.223.49.56:8081 · usuario aza · clave AzaLab2026Db"],
       ["Aplicación (local)", "http://127.0.0.1:8000"],
       ["Usuarios de prueba", "ldaza · jsarabia · dparedes · PIN 1234 (servicio/servicio solo API)"],
       ["Repositorio", "https://github.com/leodza/aza-prototipo"],
       ["Documentación interna", "App-Funcional/README.md y App-Funcional/GUIA-AWS.md"],
       ["Manual de uso", "documentos/Manual_de_Uso_AZA.docx"],
       ["Arquitectura de datos", "documentos/Arquitectura_de_Datos_AZA.docx"]],
      anchos=[5.4, 11.0], fuente=8.5)

p("")
p("Preparado por el equipo del proyecto · Noviembre de 2026", size=8.5, italic=True,
  color=RGBColor(0x78, 0x90, 0x9C), align="c")

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
doc.save(SALIDA)
print("guardado:", SALIDA)
print("figuras:", figuras[0])
