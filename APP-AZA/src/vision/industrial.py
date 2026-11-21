# vision/industrial.py — Lógica de aprobación/rechazo industrial
import sqlite3
from src.core.config import DB_PATH


def procesar_analisis_industrial(angulo_detectado, nombre_receta, operador=None, lote=None, carpeta=None):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT min_tol, max_tol FROM configuracion_recetas WHERE nombre = ?",
        (nombre_receta,)
    )
    limites = cursor.fetchone()

    if limites:
        min_t, max_t = limites
        if min_t <= angulo_detectado <= max_t:
            estado = "APROBADO"
            color = "#00FF00"
        else:
            estado = "RECHAZADO"
            color = "#FF0000"
    else:
        estado = "SIN RECETA"
        color = "#FFFFFF"

    cursor.execute("""
        INSERT INTO registros (receta, angulo, estado, operador, lote, carpeta)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nombre_receta, angulo_detectado, estado, operador, lote, carpeta))

    conn.commit()
    conn.close()
    return estado, color
