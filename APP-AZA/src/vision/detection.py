# vision/detection.py — Detección geométrica y utilidades
import cv2
import numpy as np


def calcular_angulo(cx, cy, px, py):
    """Calcula el ángulo polar (0–360°) desde el centro (cx,cy) hacia el punto (px,py)."""
    dx = px - cx
    dy = cy - py
    return np.degrees(np.arctan2(dy, dx)) % 360


def detectar_circulos(imagen_rgb):
    """Detecta círculos usando HoughCircles. Retorna None o el array de círculos."""
    gray = cv2.cvtColor(imagen_rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.medianBlur(gray, 7)

    return cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.4,
        minDist=700,
        param1=25,
        param2=35,
        minRadius=100,
        maxRadius=110
    )


def recortar_roi_circular(img, centro, radio, margen=1.3):
    """Recorta una región circular centrada en `centro` y retorna ROI + nuevo centro relativo."""
    x, y = centro
    r = int(radio * margen)

    mask = np.zeros_like(img)
    cv2.circle(mask, (x, y), r, (255, 255, 255), -1)

    masked = cv2.bitwise_and(img, mask)

    x0 = max(x - r, 0)
    y0 = max(y - r, 0)
    x1 = min(x + r, img.shape[1])
    y1 = min(y + r, img.shape[0])

    roi = masked[y0:y1, x0:x1]
    nuevo_centro = (x - x0, y - y0)

    return roi, nuevo_centro
