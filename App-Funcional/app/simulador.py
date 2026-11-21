"""Simulador de cámara y ráfagas de inspección.

Genera una ráfaga sintética de imágenes BMP —equivalente a la que produciría la
cámara al recibir un flanco de trigger— y la analiza con el MISMO pipeline de
visión que usa la aplicación de planta (APP-AZA, módulo
`src.vision.sequence_analysis`). El ángulo que llega a la base de datos es, por
tanto, medido sobre la imagen y no un valor inventado.

Si el pipeline original no está disponible, se usa un medidor interno
equivalente, de modo que la demostración nunca falla.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_AZA = os.path.join(os.path.dirname(BASE_DIR), "APP-AZA")

ANCHO, ALTO = 640, 480
CX, CY, RADIO = 400, 250, 150
FRAMES_FONDO = 6
FRAMES_PIEZA = 10

# --- modelo de proceso -------------------------------------------------------
# Velocidad de referencia del tren de trefilado y sensibilidad del ángulo.
# Por sobre la nominal el material se estira y el arco de salida se abre; por
# debajo, el arco se cierra. Eso permite "corregir" la diferencia de grados
# acelerando o desacelerando.
VELOCIDAD_NOMINAL = 12.0        # m/min
VELOCIDAD_MIN = 4.0
VELOCIDAD_MAX = 30.0
DESVIACION_POR_M_MIN = 2.8      # grados por m/min respecto de la nominal
DESFASE_PIPELINE = 3.0          # el medidor reporta el borde de salida del arco

_analizador = None
_origen_pipeline = "no disponible"


def calcular_objetivo(centro: float, ancho_banda: float, velocidad: float,
                      modo: str, semilla: int | None = None) -> tuple[float, float]:
    """Calcula el ángulo que debe dibujarse y la desviación esperada.

    modo:
      · 'dentro'    → dentro de tolerancia, desplazado por la velocidad
      · 'fuera'     → deliberadamente fuera de tolerancia
      · 'aleatorio' → puede salir bien o mal, sin forzar el resultado

    Devuelve (angulo_dibujado, desviacion_respecto_del_centro).
    """
    azar = random.Random(semilla)
    velocidad = max(VELOCIDAD_MIN, min(VELOCIDAD_MAX, float(velocidad)))
    efecto_velocidad = (velocidad - VELOCIDAD_NOMINAL) * DESVIACION_POR_M_MIN

    if modo == "aleatorio":
        desviacion = azar.uniform(-0.75, 0.75) * max(ancho_banda, 20.0)
    elif modo == "fuera":
        signo = -1 if azar.random() < 0.5 else 1
        desviacion = signo * max(0.55 * ancho_banda, 24.0) + azar.uniform(-3, 3)
    else:                                   # 'dentro'
        desviacion = efecto_velocidad + azar.uniform(-1.5, 1.5)

    medido = centro + desviacion
    dibujado = medido - DESFASE_PIPELINE
    dibujado = max(6.0, min(350.0, dibujado))
    return round(dibujado, 1), round(desviacion, 1)


# --------------------------------------------------------------------------- #
# análisis (pipeline real o respaldo interno)
# --------------------------------------------------------------------------- #
def _cargar_pipeline():
    global _analizador, _origen_pipeline
    if _analizador is not None:
        return _analizador
    # 1) copia incluida en el proyecto (la que viaja en el contenedor)
    try:
        from vision_aza import analyze_sequence  # type: ignore
        _analizador = analyze_sequence
        _origen_pipeline = "pipeline APP-AZA (vision_aza)"
        return _analizador
    except Exception:
        pass
    # 2) repositorio original de la app de planta
    try:
        if APP_AZA not in sys.path:
            sys.path.insert(0, APP_AZA)
        from src.vision.sequence_analysis import analyze_sequence  # type: ignore
        _analizador = analyze_sequence
        _origen_pipeline = "pipeline APP-AZA (src.vision.sequence_analysis)"
        return _analizador
    except Exception as exc:                       # pragma: no cover
        _origen_pipeline = f"medidor interno (pipeline no disponible: {exc})"
        _analizador = _medir_interno
        return _analizador


def medir_angulo(carpeta: str) -> dict:
    """Analiza la ráfaga y devuelve un diccionario normalizado."""
    analizar = _cargar_pipeline()
    t0 = time.perf_counter()
    if analizar is _medir_interno:
        datos = _medir_interno(carpeta)
    else:
        resultado = analizar(carpeta)
        datos = {
            "angulo": resultado.exit_angle_deg,
            "confianza": resultado.angle_confidence,
            "frame_salida": resultado.first_exit_frame,
            "centro": [resultado.circle_cx, resultado.circle_cy],
            "radio": resultado.circle_radius,
            "metodo": resultado.circle_method,
            "imagen": resultado.diagnostic_path,
            "total_frames": resultado.total_frames,
        }
    datos["duracion_ms"] = int((time.perf_counter() - t0) * 1000)
    datos["motor"] = _origen_pipeline
    return datos


def _medir_interno(carpeta: str) -> dict:
    """Medidor de respaldo: umbral del arco brillante sobre el perímetro."""
    imagenes = sorted(f for f in os.listdir(carpeta) if f.startswith("img_") and f.endswith(".bmp"))
    if not imagenes:
        raise RuntimeError("La ráfaga no contiene imágenes")
    frame = cv2.imread(os.path.join(carpeta, imagenes[-1]))
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ys, xs = np.nonzero(gris >= 200)
    if len(xs) == 0:
        return {"angulo": None, "confianza": "SIN_SENAL", "frame_salida": None,
                "centro": None, "radio": None, "metodo": "interno",
                "imagen": None, "total_frames": len(imagenes)}
    cx, cy = float(xs.mean()), float(ys.mean())
    radio = float(np.mean(np.hypot(xs - CX, ys - CY)))
    angulos = np.degrees(np.arctan2(xs - cx, -(ys - cy))) % 360.0
    centro = math.degrees(math.atan2(
        float(np.mean(np.sin(np.radians(angulos)))),
        float(np.mean(np.cos(np.radians(angulos))))) ) % 360.0
    rel = ((angulos - centro + 180.0) % 360.0) - 180.0
    angulo = (centro + float(np.percentile(rel, 5))) % 360.0
    return {"angulo": round(angulo, 1), "confianza": "MEDIA", "frame_salida": 1,
            "centro": [round(cx, 1), round(cy, 1)], "radio": round(radio, 1),
            "metodo": "interno", "imagen": None, "total_frames": len(imagenes)}


# --------------------------------------------------------------------------- #
# generación de la ráfaga
# --------------------------------------------------------------------------- #
def _fondo(rng: np.random.Generator) -> np.ndarray:
    return np.clip(rng.normal(5, 1.5, (ALTO, ANCHO, 3)), 0, 255).astype(np.uint8)


def _con_pieza(rng: np.random.Generator, desde: float, hasta: float) -> np.ndarray:
    img = _fondo(rng)
    cv2.circle(img, (CX, CY), RADIO, (25, 25, 25), -1)
    ys, xs = np.indices((ALTO, ANCHO))
    dist = np.hypot(xs - CX, ys - CY)
    ang = np.degrees(np.arctan2(xs - CX, -(ys - CY))) % 360.0
    banda = (dist >= RADIO - 40) & (dist <= RADIO)
    if desde <= hasta:
        arco = (ang >= desde) & (ang <= hasta)
    else:
        arco = (ang >= desde) | (ang <= hasta)
    img[banda & arco] = 235
    return img


def generar_rafaga(carpeta: str, desde: float | None = None,
                   ancho_arco: float = 60.0, semilla: int | None = None) -> dict:
    """Crea una ráfaga sintética de 16 imágenes BMP en `carpeta`.

    `desde` es el borde de salida del arco brillante, medido en grados desde las
    12 en sentido horario; es el valor que el pipeline debería recuperar.
    """
    os.makedirs(carpeta, exist_ok=True)
    rng = np.random.default_rng(semilla)
    desde = round(rng.uniform(28, 118), 1) if desde is None else float(desde)
    hasta = (desde + ancho_arco) % 360.0

    total = 0
    for i in range(1, FRAMES_FONDO + 1):
        cv2.imwrite(os.path.join(carpeta, f"img_{i:03d}.bmp"), _fondo(rng))
        total += 1
    for i in range(FRAMES_FONDO + 1, FRAMES_FONDO + FRAMES_PIEZA + 1):
        cv2.imwrite(os.path.join(carpeta, f"img_{i:03d}.bmp"), _con_pieza(rng, desde, hasta))
        total += 1

    return {
        "carpeta": carpeta,
        "frames": total,
        "angulo_dibujado": desde,
        "arco": [desde, hasta],
        "arco_grados": ancho_arco,
    }
