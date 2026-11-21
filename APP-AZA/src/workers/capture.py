# workers/capture.py — Manager de captura trigger
import os
import time
import threading
import queue
import cv2
import numpy as np


class TriggerCaptureManager:
    """
    Recibe frames trigger (BGR), guarda a disco en carpeta de sesión,
    analiza solo hasta encontrar el primer ángulo.
    """
    def __init__(self, output_dir: str, on_first_angle_cb, on_error_cb=None):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.on_first_angle_cb = on_first_angle_cb
        self.on_error_cb = on_error_cb

        self.running = False
        self.counter = 0
        self.first_angle_saved = False

        self._q = queue.Queue(maxsize=500)
        self._th = None

    def start(self):
        self.running = True
        self._th = threading.Thread(target=self._worker, daemon=True)
        self._th.start()

    def stop(self):
        self.running = False
        try:
            self._q.put_nowait(None)
        except Exception:
            pass
        if self._th is not None:
            self._th.join(timeout=5)

    def enqueue(self, frame_bgr: np.ndarray, ts: float):
        if not self.running:
            return
        try:
            self._q.put_nowait((frame_bgr, ts))
        except queue.Full:
            pass

    def _worker(self):
        from src.vision.pipeline import detectar_angulo_en_imagen_path

        while self.running:
            try:
                item = self._q.get()
                if item is None:
                    break

                frame_bgr, ts = item
                self.counter += 1

                fname = f"{self.counter:06d}_{ts:.6f}.png"
                fpath = os.path.join(self.output_dir, fname)

                cv2.imwrite(fpath, frame_bgr)

                if not self.first_angle_saved:
                    try:
                        ang = detectar_angulo_en_imagen_path(fpath)
                        if ang is not None:
                            self.first_angle_saved = True
                            self.on_first_angle_cb(float(ang), fpath)
                    except Exception as e:
                        if self.on_error_cb:
                            self.on_error_cb(e)

            except Exception as e:
                if self.on_error_cb:
                    self.on_error_cb(e)
