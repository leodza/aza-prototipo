# vision/pipeline.py — Pipeline completo de análisis de imágenes
import os
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from sklearn.cluster import KMeans

from src.vision.detection import calcular_angulo, detectar_circulos, recortar_roi_circular


def procesar_directorio(input_dir, progress_cb=None):
    """
    Procesa todas las imágenes del directorio y genera carpetas en RESULTADO_ANALISIS/.
    progress_cb: callable(current, total) para reportar avance.
    """
    base = "RESULTADO_ANALISIS"
    carpetas = {
        "ROI": "1_ROI",
        "ANGULOS": "2_CIRCULO",
        "CLUSTER": "3_CLUSTER",
        "CLUSTER_MAYOR": "4_CLUSTER_MAYOR",
        "CANNY": "5_CANNY",
        "EXTREMO": "6_EXTREMO",
        "FINAL": "7_FINAL"
    }

    for sub in carpetas.values():
        path = os.path.join(base, sub)
        os.makedirs(path, exist_ok=True)
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))

    intensidad = 1.2
    k_clusters = 8

    files = sorted(
        f for f in os.listdir(input_dir)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    )

    centros = []
    radios = []

    total = len(files)
    for i, fn in enumerate(files):
        img_bgr = cv2.imread(os.path.join(input_dir, fn))
        if img_bgr is None:
            continue

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        rojo = img_rgb.copy()
        rojo[:, :, 1:] = 0
        rojo = np.clip(
            rojo.astype(np.float32) * [intensidad, 1, 1],
            0, 255
        ).astype(np.uint8)

        circulos = detectar_circulos(rojo)

        if circulos is not None:
            x, y, r = np.uint16(np.around(circulos))[0][0]
            centros.append((x, y))
            radios.append(r)

        if progress_cb:
            progress_cb(i + 1, total * 2)

    if not centros:
        raise RuntimeError("No se detectó ningún círculo")

    cx_avg, cy_avg = np.mean(centros, axis=0).astype(int)
    r_avg = int(np.mean(radios))

    for j, fn in enumerate(files):
        img_bgr = cv2.imread(os.path.join(input_dir, fn))
        if img_bgr is None:
            continue
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        roi, (cx, cy) = recortar_roi_circular(img_rgb, (cx_avg, cy_avg), r_avg)

        cv2.imwrite(
            os.path.join(base, carpetas["ROI"], f"{fn}_roi.png"),
            cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)
        )

        flat = roi.reshape(-1, 3)
        km = KMeans(n_clusters=k_clusters, n_init=10, random_state=53)
        labels = km.fit_predict(flat)
        centers = km.cluster_centers_.astype(np.uint8)

        cluster_img = centers[labels].reshape(roi.shape)

        cv2.imwrite(
            os.path.join(base, carpetas["CLUSTER"], f"{fn}_cluster.png"),
            cv2.cvtColor(cluster_img, cv2.COLOR_RGB2BGR)
        )

        idx_top = np.argmax(centers.sum(axis=1))
        mask = (labels == idx_top).reshape(roi.shape[:2])

        top = np.zeros_like(roi)
        top[mask] = roi[mask]

        cv2.imwrite(
            os.path.join(base, carpetas["CLUSTER_MAYOR"], f"{fn}_cluster_top.png"),
            cv2.cvtColor(top, cv2.COLOR_RGB2BGR)
        )

        gray = cv2.cvtColor(top, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        conts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_ang = -1
        max_pt = None

        for c in conts:
            for px, py in c[:, 0]:
                d = np.hypot(px - cx, py - cy)
                if d > r_avg:
                    continue
                ang = calcular_angulo(cx, cy, px, py)
                if ang > max_ang:
                    max_ang = ang
                    max_pt = (px, py)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(roi)
        ax.axis("off")

        ax.add_patch(plt.Circle((cx, cy), r_avg, fill=False, color="lime", linewidth=2))

        if max_pt:
            ax.plot([cx, max_pt[0]], [cy, max_pt[1]], "--b")
            color = "green" if 180 <= max_ang <= 270 else "red"
            ax.add_patch(Wedge((cx, cy), r_avg, -max_ang, 0, color=color, alpha=0.3))
            ax.plot(max_pt[0], max_pt[1], "bx", markersize=15, mew=3)

        fig.savefig(
            os.path.join(base, carpetas["FINAL"], f"{fn}_final.png"),
            dpi=150,
            bbox_inches="tight"
        )
        plt.close(fig)

        if progress_cb:
            progress_cb(total + j + 1, total * 2)


def detectar_angulo_en_imagen_path(image_path: str):
    """Devuelve ángulo (float) o None si no logra detectar. NO escribe resultados a disco."""
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return None

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    intensidad = 1.2
    k_clusters = 8

    rojo = img_rgb.copy()
    rojo[:, :, 1:] = 0
    rojo = np.clip(
        rojo.astype(np.float32) * [intensidad, 1, 1],
        0, 255
    ).astype(np.uint8)

    circulos = detectar_circulos(rojo)
    if circulos is None:
        return None

    x, y, r = np.uint16(np.around(circulos))[0][0]
    roi, (cx, cy) = recortar_roi_circular(img_rgb, (int(x), int(y)), int(r))

    flat = roi.reshape(-1, 3)
    km = KMeans(n_clusters=k_clusters, n_init=10, random_state=53)
    labels = km.fit_predict(flat)
    centers = km.cluster_centers_.astype(np.uint8)

    idx_top = int(np.argmax(centers.sum(axis=1)))
    mask = (labels == idx_top).reshape(roi.shape[:2])

    top = np.zeros_like(roi)
    top[mask] = roi[mask]

    gray = cv2.cvtColor(top, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    conts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_ang = -1.0
    max_pt = None

    for c in conts:
        for px, py in c[:, 0]:
            d = np.hypot(px - cx, py - cy)
            if d > r:
                continue
            ang = calcular_angulo(cx, cy, px, py)
            if ang > max_ang:
                max_ang = ang
                max_pt = (px, py)

    if max_pt is None:
        return None

    return float(max_ang)


def obtener_imagenes_finales():
    """Retorna lista de imágenes finales generadas."""
    path = os.path.join("RESULTADO_ANALISIS", "7_FINAL")
    if not os.path.isdir(path):
        return []
    return [
        os.path.join(path, f)
        for f in sorted(os.listdir(path))
        if f.endswith(".png")
    ]
