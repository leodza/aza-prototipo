"""Captura de rafagas por flanco de subida en Line0."""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, Signal

from src.core.config import GENTL_DIR_DEFAULT
from src.vision.sequence_analysis import analyze_sequence

os.environ.setdefault("GENICAM_GENTL64_PATH", GENTL_DIR_DEFAULT)

try:
    import neoapi
except ImportError:
    neoapi = None


logger = logging.getLogger(__name__)


class SequenceBurstManager(QObject):
    burst_started = Signal(int)
    burst_complete = Signal(str, list)
    analysis_complete = Signal(object)
    error = Signal(str)
    status = Signal(str)
    frames_captured = Signal(int, int)
    temp_ready = Signal(object)
    stopped = Signal()

    def __init__(
        self,
        output_dir: str,
        frame_count: int = 100,
        exposure_time: float = 1000.0,
        frame_rate: float | None = None,
        device_id: str | None = None,
    ):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.frame_count = frame_count
        self.exposure_time = exposure_time
        self.frame_rate = frame_rate
        self.device_id = device_id
        self.running = False
        self._thread = None
        self._camera = None
        self._camera_lock = threading.RLock()
        self._trigger_counter = self._last_trigger_counter()
        self._burst_timeout_ms = 500
        self._max_consecutive_timeouts = 3

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker, daemon=False)
        self._thread.start()

    def stop(self):
        self.running = False
        self._request_camera_stop()
        if self._thread is not None:
            self._thread.join(timeout=30)
            if self._thread.is_alive():
                logger.warning("El hilo de captura no se detuvo dentro de 30s")
                self._request_camera_stop(disconnect=True)

    def _request_camera_stop(self, disconnect: bool = False):
        with self._camera_lock:
            camera = self._camera
            if camera is None:
                return
            try:
                camera.f.AcquisitionStop.Execute()
            except Exception:
                pass
            try:
                if hasattr(camera.f, "TriggerMode"):
                    self._try_set(camera.f.TriggerMode, "Off")
            except Exception:
                pass
            if disconnect:
                try:
                    camera.Disconnect()
                except Exception:
                    pass

    @staticmethod
    def _try_set(feature, value):
        try:
            if isinstance(value, str) and hasattr(feature, "SetString"):
                feature.SetString(value)
            elif hasattr(feature, "Set"):
                feature.Set(value)
            else:
                feature.value = value
        except Exception:
            logger.debug("No se pudo configurar feature=%s value=%s", feature, value)

    def _tune_gige(self, features):
        if hasattr(features, "GevSCPSPacketSize"):
            for packet_size in (9000, 8192, 6000, 3000, 1500):
                before = None
                try:
                    before = int(features.GevSCPSPacketSize.Get())
                except Exception:
                    pass
                self._try_set(features.GevSCPSPacketSize, packet_size)
                try:
                    after = int(features.GevSCPSPacketSize.Get())
                    if after != before:
                        logger.info("GevSCPSPacketSize=%s", after)
                    if after >= packet_size:
                        break
                except Exception:
                    break
        if hasattr(features, "GevSCPD"):
            self._try_set(features.GevSCPD, 0)

    def _configure_basic(self, features):
        if hasattr(features, "TriggerMode"):
            self._try_set(features.TriggerMode, "Off")
        if hasattr(features, "AcquisitionMode"):
            self._try_set(features.AcquisitionMode, "MultiFrame")
        if hasattr(features, "AcquisitionFrameCount"):
            self._try_set(features.AcquisitionFrameCount, self.frame_count)
        if hasattr(features, "ExposureAuto"):
            self._try_set(features.ExposureAuto, "Off")
        if hasattr(features, "ExposureTime"):
            self._try_set(features.ExposureTime, self.exposure_time)
        if hasattr(features, "AcquisitionFrameRateEnable"):
            self._try_set(features.AcquisitionFrameRateEnable, self.frame_rate is not None)
        if self.frame_rate is not None and hasattr(features, "AcquisitionFrameRate"):
            self._try_set(features.AcquisitionFrameRate, self.frame_rate)
        if hasattr(features, "PixelFormat"):
            self._try_set(features.PixelFormat, "BayerRG8")
        self._tune_gige(features)
        if hasattr(features, "LineSelector"):
            self._try_set(features.LineSelector, "Line0")

    @staticmethod
    def _read_temperature(camera):
        try:
            features = camera.f
            if hasattr(features, "DeviceTemperature"):
                try:
                    return float(features.DeviceTemperature.value)
                except Exception:
                    pass
            if hasattr(features, "OpticControllerTemperature"):
                try:
                    return float(features.OpticControllerTemperature.value)
                except Exception:
                    pass
        except Exception:
            return None
        return None

    def _emit_temperature(self, camera):
        self.temp_ready.emit(self._read_temperature(camera))

    @staticmethod
    def _log_camera_list():
        if neoapi is None:
            return
        try:
            camera_list = neoapi.CamInfoList.Get()
            logger.info("NeoAPI detecta %d camaras", camera_list.size())
            for index in range(camera_list.size()):
                info = camera_list[index]
                logger.info(
                    "Camara %d: id=%s vendor=%s model=%s serial=%s ip=%s connectable=%s",
                    index,
                    info.GetId(),
                    info.GetVendorName(),
                    info.GetModelName(),
                    info.GetSerialNumber(),
                    info.GetGevIpAddress(),
                    info.IsConnectable(),
                )
        except Exception:
            logger.debug("No se pudo listar camaras NeoAPI", exc_info=True)

    def _connect_camera(self, camera):
        last_exc = None
        for attempt in range(1, 4):
            if not self.running:
                raise RuntimeError("Conexion cancelada")
            try:
                if self.device_id:
                    camera.Connect(self.device_id)
                else:
                    camera.Connect()
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "No se pudo conectar camara en intento %d/3: %s",
                    attempt,
                    exc,
                )
                self._log_camera_list()
                time.sleep(1.5)
        raise last_exc

    def _configure(self, camera):
        features = camera.f
        try:
            features.AcquisitionStop.Execute()
        except Exception:
            pass
        if hasattr(features, "SequencerMode"):
            self._try_set(features.SequencerMode, "Off")
        if hasattr(features, "SequencerConfigurationMode"):
            self._try_set(features.SequencerConfigurationMode, "Off")

        self._configure_basic(features)

    def _next_trigger_folder(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        now = time.localtime()
        day_dir = self.output_dir / time.strftime("%Y-%m-%d", now)
        timestamp = time.strftime("%Y%m%d_%H%M%S", now)
        while True:
            self._trigger_counter += 1
            folder = day_dir / f"Trigger_{self._trigger_counter:04d}_{timestamp}"
            try:
                folder.mkdir(parents=True, exist_ok=False)
                return folder
            except FileExistsError:
                continue

    def _last_trigger_counter(self) -> int:
        last_counter = 0
        if not self.output_dir.is_dir():
            return last_counter
        for path in self.output_dir.rglob("Trigger_*"):
            if not path.is_dir():
                continue
            try:
                last_counter = max(last_counter, int(path.name.split("_")[1]))
            except (IndexError, ValueError):
                continue
        return last_counter

    @staticmethod
    def _to_bgr(raw):
        if raw.ndim == 2:
            return cv2.cvtColor(raw, cv2.COLOR_BAYER_RG2BGR)
        if raw.ndim == 3 and raw.shape[2] == 3:
            return cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
        return raw

    def _capture_burst(self, camera, folder: Path):
        paths = []
        try:
            camera.f.AcquisitionStop.Execute()
            time.sleep(0.1)
        except Exception:
            pass

        try:
            camera.f.AcquisitionStart.Execute()
        except Exception:
            logger.exception("Fallo AcquisitionStart; reintentando una vez")
            try:
                camera.f.AcquisitionStop.Execute()
                time.sleep(0.5)
                camera.f.AcquisitionStart.Execute()
            except Exception:
                logger.exception("Fallo definitivo iniciando adquisicion")
                raise

        capture_start = time.perf_counter()
        consecutive_timeouts = 0
        try:
            for index in range(self.frame_count):
                if not self.running:
                    break
                image = camera.GetImage(self._burst_timeout_ms)
                if image.IsEmpty():
                    consecutive_timeouts += 1
                    logger.warning("Timeout en imagen %d", index + 1)
                    if paths and consecutive_timeouts >= self._max_consecutive_timeouts:
                        logger.warning(
                            "Cortando rafaga por %d timeouts consecutivos despues de %d frames",
                            consecutive_timeouts,
                            len(paths),
                        )
                        break
                    continue
                consecutive_timeouts = 0
                frame = self._to_bgr(image.GetNPArray())
                path = folder / f"img_{len(paths) + 1:03d}.bmp"
                if cv2.imwrite(str(path), frame):
                    paths.append(str(path))
                    self.frames_captured.emit(len(paths), self.frame_count)
                del image
                del frame
        finally:
            try:
                camera.f.AcquisitionStop.Execute()
            except Exception:
                pass
            time.sleep(0.05)

        elapsed = time.perf_counter() - capture_start
        if len(paths) > 1 and elapsed > 0:
            logger.info(
                "Rafaga post-trigger: %d frames en %.3fs",
                len(paths),
                elapsed,
            )
        return paths

    def _discard_folder(self, folder: Path):
        for path in folder.glob("img_*.bmp"):
            try:
                path.unlink()
            except OSError:
                logger.debug("No se pudo eliminar captura descartada: %s", path)
        try:
            folder.rmdir()
        except OSError:
            pass

    @staticmethod
    def _line_is_high(camera) -> bool:
        try:
            return bool(camera.f.LineStatus.Get())
        except Exception:
            try:
                return bool(camera.f.LineStatus.GetValue())
            except Exception:
                return False

    def _worker(self):
        if neoapi is None:
            self.error.emit("neoapi no esta instalado en este entorno")
            self.running = False
            self.stopped.emit()
            return

        camera = neoapi.Cam()
        with self._camera_lock:
            self._camera = camera
        try:
            self.status.emit("Conectando camara...")
            self._connect_camera(camera)
            self._configure(camera)
            self._emit_temperature(camera)
            self.status.emit("Esperando senal de trigger en Line0...")
            previous = self._line_is_high(camera)
            logger.info("Line0 estado inicial: %s", previous)

            while self.running:
                self.status.emit("Esperando senal de trigger en Line0...")
                current = self._line_is_high(camera)
                if current != previous:
                    logger.info("Line0 cambio: %s -> %s", previous, current)
                if not (current and not previous):
                    previous = current
                    time.sleep(0.001)
                    continue

                self._emit_temperature(camera)
                folder = self._next_trigger_folder()
                self.burst_started.emit(self.frame_count)
                self.status.emit(f"Trigger detectado. Capturando {self.frame_count} imagenes...")
                paths = self._capture_burst(camera, folder)
                if not self.running:
                    break
                if not paths:
                    self._discard_folder(folder)
                    previous = current
                    continue

                self.status.emit(f"Trigger detectado. Capturadas {len(paths)} imagenes.")
                self._emit_temperature(camera)
                if len(paths) < 2:
                    self.error.emit("El trigger no produjo suficientes imagenes")
                else:
                    self.burst_complete.emit(str(folder), paths)
                    self.status.emit("Analizando rafaga...")
                    try:
                        result = analyze_sequence(folder)
                        self.analysis_complete.emit(result)
                        self.status.emit("Analisis terminado. Esperando siguiente trigger...")
                    except Exception as exc:
                        logger.exception("Error analizando %s", folder)
                        self.error.emit(f"Fallo el analisis de {folder.name}: {exc}")
                previous = current
        except Exception as exc:
            logger.exception("Error en operacion trigger")
            self.error.emit(str(exc))
        finally:
            with self._camera_lock:
                try:
                    camera.f.AcquisitionStop.Execute()
                except Exception:
                    pass
                try:
                    if hasattr(camera.f, "TriggerMode"):
                        self._try_set(camera.f.TriggerMode, "Off")
                except Exception:
                    pass
                try:
                    if hasattr(camera.f, "SequencerMode"):
                        self._try_set(camera.f.SequencerMode, "Off")
                except Exception:
                    pass
                try:
                    camera.Disconnect()
                except Exception:
                    pass
                self._camera = None
            self.running = False
            self.stopped.emit()
