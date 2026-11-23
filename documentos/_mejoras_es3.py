# -*- coding: utf-8 -*-
"""Mejoras al Informe de Gestión ES3: índices, prueba de carga y datos actualizados."""
import os
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(RAIZ, "ES3-informe tecnico", "Informe_de_Gestion_AZA_ES3 (2).docx")
RESPALDO = os.path.join(RAIZ, "ES3-informe tecnico", "Informe_de_Gestion_AZA_ES3 (2) - respaldo.docx")
EVID = os.path.join(RAIZ, "App-Funcional", "evidencias")

if not os.path.exists(RESPALDO):
    shutil.copy2(DOCX, RESPALDO)
    print("respaldo creado")

doc = Document(DOCX)
ESTILO_TABLA = doc.tables[0].style.name
print("estilo de tabla:", ESTILO_TABLA)


def parrafo(texto, estilo=None, negrita=False, cursiva=False, tam=None, centrado=False):
    p = doc.add_paragraph(style=estilo)
    r = p.add_run(texto)
    r.bold = negrita
    r.italic = cursiva
    if tam:
        r.font.size = Pt(tam)
    if centrado:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def tabla(filas, anchos=None, fuente=9):
    t = doc.add_table(rows=0, cols=len(filas[0]))
    t.style = ESTILO_TABLA
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = ""
            p = celdas[i].paragraphs[0]
            r = p.add_run(str(valor))
            r.font.size = Pt(fuente)
            r.bold = (n == 0)
            if anchos:
                celdas[i].width = Cm(anchos[i])
    return t


def mover_antes(ref_par, elementos):
    for el in elementos:
        xml = el._p if hasattr(el, "_p") else el._tbl
        ref_par._p.addprevious(xml)


def insertar_bloque(ref_par, elementos):
    """Coloca los elementos antes del párrafo de referencia, en orden."""
    for el in elementos:
        xml = el._p if hasattr(el, "_p") else el._tbl
        ref_par._p.addprevious(xml)


# ---------------------------------------------------------------- 1. texto
cambios = {
    63: ("El historial de Git agrupa diecinueve commits por módulo: modelo, simulador, API, "
         "interfaz, pruebas, despliegue y evidencias, más los de la revisión de cierre (Figura 7). "
         "Los mensajes describen el alcance de cada cambio y permiten reconstruir el orden de construcción."),
    157: "Nota. Historial de Git con diecinueve commits agrupados por módulo. Los mensajes describen "
         "el alcance de cada cambio y permiten reconstruir el orden de construcción.",
    118: "La base tiene veintitrés índices: dieciséis de clave primaria o de unicidad y siete "
         "secundarios incorporados durante esta revisión (fecha_hora, estado, receta_id, lote_id, "
         "batch_id, el compuesto fecha_hora–id y la fecha de la auditoría). A sesenta y tres filas el "
         "planificador todavía prefiere el recorrido secuencial, porque el volumen no justifica el "
         "índice; a cien mil filas la diferencia medida es de 306 veces. Los índices quedan listos "
         "para ese escenario.",
    119: "Los índices ya no son una brecha de diseño: están declarados en el modelo (index=True) y su "
         "DDL se aplica con deploy/indices.sql. Lo que queda es medir el efecto con volumen real, que "
         "es una tarea de producción y no del prototipo. El ES2 ya los preveía; la implementación "
         "quedó completa en esta revisión.",
    180: "Las pruebas de carga y de estrés ya se ejecutaron (sección 6.5 y Anexo D): midieron latencia "
         "por endpoint, concurrencia, escrituras simultáneas y el costo del análisis de visión, e "
         "identificaron el límite real del sistema. Siguen pendientes las pruebas E2E de navegador y "
         "HTTPS, y la cobertura de S3 es baja porque la suite no levanta un bucket real. Estas "
         "limitaciones están en el plan de cierre y no se ocultan; lo que cambia es que ahora tienen "
         "una acción y una fecha.",
    190: "Durante la revisión se corrigió el detalle de la auditoría que se mostraba como "
         "[object Object], se alineó la clave de pgweb con la documentación, se ejecutó la prueba de "
         "respaldo y restauración y se agregaron los siete índices secundarios al modelo. Además se "
         "ejecutó la prueba de carga y estrés que el informe anterior declaraba pendiente, y se "
         "actualizó el conteo de commits a diecinueve. Todos los cambios están aplicados en el "
         "repositorio y en el entorno.",
}

for indice, texto in cambios.items():
    p = doc.paragraphs[indice]
    for run in p.runs:
        run.text = ""
    if p.runs:
        p.runs[0].text = texto
    else:
        p.add_run(texto)
    print(f"  párrafo {indice} actualizado")

# ------------------------------------------------- 2. sección 6.5 en el cuerpo
ref = doc.paragraphs[182]          # «7. Riesgos»
h65 = parrafo("6.5 Prueba de carga y estrés", estilo="Heading 2")
p1 = parrafo(
    "Se ejecutó una prueba de carga y estrés con cuatro escenarios: latencia por endpoint, lecturas "
    "concurrentes, escrituras simultáneas y análisis de visión completo. Se midió sobre el servidor "
    "local con SQLite y sobre el despliegue en AWS con PostgreSQL, con el mismo generador de carga. "
    "El procedimiento y los resultados completos están en el Anexo D (Tabla 19, Figuras 8 y 9).")
p2 = parrafo(
    "Los resultados confirman el comportamiento esperado en lecturas —el tablero responde en 8,6 ms "
    "de percentil 95 y el histórico en 28,7 ms— y descubren el límite del sistema: las escrituras "
    "concurrentes no escalan sobre SQLite (8,1 registros por segundo con cualquier cantidad de "
    "clientes, y 3.480 ms de latencia p95 con diez), mientras que PostgreSQL alcanza 51,0 registros "
    "por segundo y mantiene 307 ms en el mismo escenario. Esa medición es la justificación empírica "
    "del motor elegido en el ES2 y el argumento para no volver a SQLite en producción.")
p3 = parrafo(
    "El segundo hallazgo es operativo: el servidor corre con un solo proceso, de modo que el "
    "rendimiento se estanca cerca de 80 peticiones por segundo aunque se agreguen clientes. La "
    "recomendación es ejecutar uvicorn con varios workers y desplegar en una región más cercana, "
    "porque la red hacia us-east-1 suma unos 140 ms a cada petición.")
insertar_bloque(ref, [h65, p1, p2, p3])
print("  sección 6.5 insertada")

# --------------------------------------------------------- 3. Anexo D al final
hD = parrafo("Anexo D. Prueba de carga y estrés", estilo="Heading 2")
a1 = parrafo(
    "Objetivo. Medir el comportamiento del sistema bajo carga y encontrar el límite antes de la "
    "puesta en marcha, con números verificables y reproducibles.")
a2 = parrafo(
    "Método. Se usó un generador propio (pruebas_carga/estres.py) que abre conexiones concurrentes "
    "reales contra la API, registra la latencia de cada petición y calcula media, p50, p95, p99 y "
    "tasa de error. Se ejecutaron cuatro escenarios: (1) 60 peticiones secuenciales a cuatro "
    "endpoints; (2) lecturas concurrentes con 1, 5, 10 y 20 clientes durante 12 segundos por nivel; "
    "(3) 40 escrituras por nivel con 1, 5 y 10 clientes; (4) el análisis completo de una ráfaga de "
    "16 imágenes. La misma prueba se corrió contra SQLite en el equipo y contra PostgreSQL en AWS.")
a3 = parrafo("La Tabla 19 compara ambos entornos en las métricas que decidieron el diseño.")
capT = parrafo("Tabla 19", negrita=True)
titT = parrafo("Resultados de la prueba de carga en ambos entornos")
t19 = tabla([
    ["Métrica", "SQLite (equipo local)", "PostgreSQL (AWS)"],
    ["Dashboard · latencia p95", "8,6 ms", "143,5 ms"],
    ["Histórico (20 filas) · p95", "28,7 ms", "152,5 ms"],
    ["Lecturas con 20 clientes", "78,0 req/s", "73,0 req/s"],
    ["Lecturas con 20 clientes · p95", "642 ms", "471 ms"],
    ["Escrituras con 1 cliente", "8,7 reg/s", "6,5 reg/s"],
    ["Escrituras con 10 clientes", "8,1 reg/s", "51,0 reg/s"],
    ["Escrituras con 10 clientes · p95", "3.480 ms", "307 ms"],
    ["Ráfaga de visión (16 imágenes)", "2,34 s", "2,42 s"],
    ["Tasa de error", "0 %", "0 %"],
], anchos=[6.4, 4.8, 4.8])
notaT = parrafo(
    "Nota. Elaboración propia. Medición del 22-11-2026. La latencia del entorno en AWS incluye la red "
    "entre Santiago y us-east-1 (unos 140 ms por petición), por lo que no representa el tiempo de "
    "cómputo del servidor. Los scripts y los resultados crudos están en App-Funcional/pruebas_carga/.",
    cursiva=True, tam=8.5)

a4 = parrafo(
    "La Figura 8 muestra el comportamiento de las lecturas concurrentes: el rendimiento se estanca "
    "mientras la latencia crece, señal de que el cuello de botella es el proceso único del servidor y "
    "no la base de datos.")
f8 = doc.add_paragraph()
f8.alignment = WD_ALIGN_PARAGRAPH.CENTER
f8.add_run().add_picture(os.path.join(EVID, "31_estres_concurrencia.png"), width=Cm(15.2))
cap8 = parrafo("Figura 8", centrado=True, negrita=True)
tit8 = parrafo("Lecturas concurrentes: rendimiento y latencia", centrado=True)
nota8 = parrafo("Nota. Elaboración propia con los datos de pruebas_carga/resultados.json.",
                cursiva=True, tam=8.5, centrado=True)

a5 = parrafo(
    "La Figura 9 compara las escrituras. SQLite se mantiene en 8 registros por segundo y su latencia "
    "se multiplica por veintiuno al pasar de uno a diez clientes; PostgreSQL escala hasta 51 registros "
    "por segundo y conserva una latencia acotada.")
f9 = doc.add_paragraph()
f9.alignment = WD_ALIGN_PARAGRAPH.CENTER
f9.add_run().add_picture(os.path.join(EVID, "37_estres_comparacion_escrituras.png"), width=Cm(15.2))
cap9 = parrafo("Figura 9", centrado=True, negrita=True)
tit9 = parrafo("Escrituras concurrentes: SQLite frente a PostgreSQL", centrado=True)
nota9 = parrafo("Nota. Elaboración propia. El panel izquierdo compara el rendimiento y el derecho la "
                "latencia p95 en el mismo escenario.", cursiva=True, tam=8.5, centrado=True)

a6 = parrafo(
    "Conclusiones. El sistema soporta con holgura la operación prevista de un operador por línea: una "
    "ráfaga tarda 2,3 segundos, el consumo de memoria se mantiene bajo y no se produjo un solo error "
    "en las cuatro corridas. El límite aparece con varios operadores escribiendo a la vez, y ahí la "
    "medición respalda la decisión de PostgreSQL. Las dos acciones que siguen son ejecutar el servidor "
    "con varios workers y desplegar en una región más cercana; ambas son de configuración, no de "
    "código. La prueba es reproducible con los scripts del repositorio y queda como línea base para "
    "comparar futuras versiones.")

# El anexo va al final del documento, después del glosario
for el in [hD, a1, a2, a3, capT, titT, t19, notaT, a4, f8, cap8, tit8, nota8, a5, f9, cap9, tit9, nota9, a6]:
    xml = el._p if hasattr(el, "_p") else el._tbl
    doc.element.body.append(xml)
print("  Anexo D agregado")

doc.save(DOCX)
print("guardado:", DOCX)
