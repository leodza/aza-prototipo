# ui/app.py - Ventana principal AnalizadorApp
import os
import datetime
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout,
    QProgressBar
)
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QPixmap, QShortcut

from src.core.config import DEVICE_ID_DEFAULT
from src.database.auth import es_admin
from src.database.models import inicializar_db
from src.results_export import delete_result_path, export_results
from src.results_retention import (
    DEFAULT_RESULTS_LIMIT_BYTES,
    cleanup_plan,
    delete_burst_folders,
    directory_size,
)
from src.result_items import result_item_for
from src.vision.sequence_analysis import is_sequence_folder
from src.workers.analysis import SavedSequenceAnalysisThread
from src.workers.sequence import SequenceBurstManager
from src.ui.components import ResultViewer
from src.utils import resource_path

logger = logging.getLogger(__name__)
IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


class AnalizadorApp(QMainWindow):
    def __init__(self, operador: str):
        super().__init__()

        inicializar_db()
        self.operador_activo = operador
        self._is_admin = es_admin(self.operador_activo)

        self.sequence_mgr = None
        self.saved_analysis_thread = None
        self._last_result_path = None
        self._restore_fullscreen_after_minimize = False
        self._minimize_applied = False
        self._retention_prompt_open = False
        self._burst_processing_active = False

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.directorio = str(Path.home() / "Desktop" / "RESULTADOS_ANALISIS_SALIDA_ROLLO")
        self.menu_visible = False
        self.menu_width = 260
        self.last_cam_temp = None

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.side_menu = QWidget()
        self.side_menu.setFixedWidth(self.menu_width)
        self.side_menu.setStyleSheet("background-color:#1B5E20;")
        menu_layout = QVBoxLayout(self.side_menu)
        menu_layout.setContentsMargins(30, 30, 30, 30)
        menu_layout.setSpacing(15)

        def menu_button(text: str) -> QPushButton:
            b = QPushButton(text)
            b.setFixedHeight(42)
            b.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; border-radius: 6px; padding-left: 12px; text-align: left; font-weight: bold; }"
                "QPushButton:hover { background-color: #388E3C; }"
                "QPushButton:disabled { background-color: #2E7D32; color: #C8E6C9; }"
            )
            return b

        self.btn_dir = menu_button(" Seleccionar Directorio")
        self.btn_run = menu_button(" Ejecutar Analisis")
        self.btn_saved_run = menu_button(" Analizar Rafaga Guardada")
        self.btn_results = menu_button(" Ver Resultados")
        self.btn_files = menu_button(" Abrir Carpeta Resultados")
        self.btn_download = menu_button(" Descargar")
        self.btn_delete_files = menu_button(" Borrar Archivo/Carpeta")
        self._operation_buttons = [
            self.btn_dir,
            self.btn_saved_run,
            self.btn_results,
            self.btn_files,
            self.btn_download,
            self.btn_delete_files,
        ]

        menu_layout.addWidget(self.btn_dir)
        menu_layout.addWidget(self.btn_run)
        menu_layout.addWidget(self.btn_saved_run)
        menu_layout.addWidget(self.btn_results)
        menu_layout.addWidget(self.btn_files)
        menu_layout.addWidget(self.btn_download)
        menu_layout.addWidget(self.btn_delete_files)
        menu_layout.addStretch()

        self.btn_dir.clicked.connect(self.seleccionar_directorio)
        self.btn_run.clicked.connect(self.ejecutar_analisis)
        self.btn_saved_run.clicked.connect(self.analizar_rafaga_guardada)
        self.btn_results.clicked.connect(self.ver_resultados)
        self.btn_files.clicked.connect(self.abrir_carpeta_resultados)
        self.btn_download.clicked.connect(self.descargar_resultados)
        self.btn_delete_files.clicked.connect(self.borrar_archivo_o_carpeta)

        if not self._is_admin:
            self.btn_delete_files.setEnabled(False)
            self.btn_delete_files.setToolTip("Solo admin puede borrar archivos o carpetas.")

        self.content = QWidget()
        self.content.setStyleSheet("background-color: #121212;")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.top_widget = QWidget()
        top_l = QHBoxLayout(self.top_widget)
        top_l.setContentsMargins(20, 20, 20, 10)

        btn_toggle = QPushButton()
        btn_toggle.setText("Menu")
        btn_toggle.setFixedSize(42, 42)
        btn_toggle.setStyleSheet("background: #333; color: white; border-radius: 5px; font-size: 18px;")
        btn_toggle.clicked.connect(self.toggle_menu)

        self.lbl_datetime = QLabel("")
        self.lbl_datetime.setStyleSheet("color: rgba(255,255,255,180); font-size: 13px; font-weight: 500;")
        self.lbl_datetime.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        btn_minimize = QPushButton(" Minimizar")
        btn_minimize.setStyleSheet(
            "background-color:#424242; color:white; padding: 8px 20px; "
            "font-weight:bold; border-radius:5px;"
        )
        btn_minimize.clicked.connect(self.minimizar_ventana)

        btn_exit = QPushButton(" Salir")
        btn_exit.setStyleSheet("background-color:#C62828; color:white; padding: 8px 20px; font-weight:bold; border-radius:5px;")
        btn_exit.clicked.connect(QApplication.quit)

        top_l.addWidget(btn_toggle)
        top_l.addStretch()
        top_l.addWidget(self.lbl_datetime)
        top_l.addSpacing(20)
        top_l.addWidget(btn_minimize)
        top_l.addSpacing(10)
        top_l.addWidget(btn_exit)
        content_layout.addWidget(self.top_widget)

        self.shortcut_minimize = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_minimize.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_minimize.activated.connect(self.minimizar_ventana)

        content_layout.addStretch(0)

        image_area = QWidget()
        image_layout = QHBoxLayout(image_area)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        self.logo_label = QLabel(alignment=Qt.AlignCenter)
        self.logo_label.setMinimumSize(900, 600)
        self.result_frame_label = QLabel(alignment=Qt.AlignCenter)
        self.result_frame_label.hide()
        logo_path = resource_path(os.path.join("assets", "logo.png"))
        if os.path.exists(logo_path):
            self.logo_label.setPixmap(QPixmap(logo_path).scaled(450, 400, Qt.AspectRatioMode.KeepAspectRatio))
        image_layout.addWidget(self.logo_label, 1)
        image_layout.addWidget(self.result_frame_label, 1)
        content_layout.addWidget(image_area)

        content_layout.addSpacing(12)

        self.estado = QLabel(
            f"Directorio de resultados: {self.directorio}",
            alignment=Qt.AlignCenter,
        )
        self.estado.setStyleSheet("color: #4CAF50; font-size: 18px; font-weight: 500;")
        content_layout.addWidget(self.estado)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setFixedWidth(500)
        self.progress.setStyleSheet("QProgressBar { border: none; background: #222; } QProgressBar::chunk { background: #4CAF50; }")
        self.progress.hide()
        content_layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        content_layout.addStretch(0)

        self.status_widget = QWidget()
        self.status_widget.setFixedHeight(45)
        self.status_widget.setStyleSheet("background-color: #0A2E0D; border-top: 2px solid #2E7D32;")
        status_l = QHBoxLayout(self.status_widget)
        status_l.setContentsMargins(30, 0, 30, 0)

        self.val_operador = QLabel(f"OP: {self.operador_activo}")
        self.val_operador.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        self.led_cam = QLabel(" NEOAPI")
        self.led_cam.setStyleSheet("color: #9E9E9E; font-weight: bold; font-size: 12px;")
        self.val_temp = QLabel("TEMP: -- C")
        self.val_temp.setStyleSheet("color: #9E9E9E; font-size: 12px; font-weight: bold;")
        self.storage_label = QLabel("RAFAGAS: -- / 40.0 GB")
        self.storage_label.setStyleSheet("color: #C8E6C9; font-size: 12px; font-weight: bold;")
        self.storage_bar = QProgressBar()
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(0)
        self.storage_bar.setFixedSize(180, 10)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #2E7D32; background: #1A1A1A; border-radius: 3px; }"
            "QProgressBar::chunk { background: #4CAF50; border-radius: 2px; }"
        )

        status_l.addWidget(self.val_operador)
        status_l.addSpacing(50)
        status_l.addWidget(self.led_cam)
        status_l.addSpacing(50)
        status_l.addWidget(self.val_temp)
        status_l.addSpacing(50)
        status_l.addWidget(self.storage_label)
        status_l.addWidget(self.storage_bar)
        status_l.addStretch()

        content_layout.addWidget(self.status_widget)

        self.footer = QWidget()
        self.footer.setFixedHeight(30)
        self.footer.setStyleSheet("background-color: #0A2E0D; border-top: 1px solid #2E7D32;")
        footer_l = QHBoxLayout(self.footer)
        footer_l.setContentsMargins(20, 0, 20, 0)
        self.lbl_footer = QLabel("Realizado por Robotic Systems Chile | soporte@roboticsystems.cl - Febrero 2026 - Version 1.0")
        self.lbl_footer.setStyleSheet("color: rgba(255,255,255,170); font-size: 12px;")
        self.lbl_footer.setAlignment(Qt.AlignCenter)
        footer_l.addStretch()
        footer_l.addWidget(self.lbl_footer)
        footer_l.addStretch()
        content_layout.addWidget(self.footer)

        root.addWidget(self.side_menu)
        root.addWidget(self.content)

        self.side_menu.hide()

        self.timer_status = QTimer()
        self.timer_status.timeout.connect(self.actualizar_barra_estado)
        self.timer_status.timeout.connect(self.actualizar_fecha_hora)
        self.timer_status.start(1000)
        self.actualizar_fecha_hora()
        self._last_storage_check = 0.0
        self.actualizar_barra_almacenamiento()

        self.retention_timer = QTimer()
        self.retention_timer.timeout.connect(self.verificar_limite_rafagas)
        self.retention_timer.start(5 * 60 * 1000)
        QTimer.singleShot(15000, self.verificar_limite_rafagas)

    def actualizar_fecha_hora(self):
        now = datetime.datetime.now()
        self.lbl_datetime.setText(now.strftime("%d-%m-%Y  |  %H:%M:%S"))

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() != QEvent.Type.WindowStateChange:
            return

        if self.isMinimized():
            self._minimize_applied = True
            return

        old_state = event.oldState() if hasattr(event, "oldState") else Qt.WindowStates()
        was_minimized = bool(old_state & Qt.WindowState.WindowMinimized)
        if (
            was_minimized
            and self._restore_fullscreen_after_minimize
            and self._minimize_applied
        ):
            self._restore_fullscreen_after_minimize = False
            self._minimize_applied = False
            QTimer.singleShot(0, self.showFullScreen)

    def minimizar_ventana(self):
        if self.isMinimized():
            return

        self._restore_fullscreen_after_minimize = self.isFullScreen()
        self._minimize_applied = False

        if self._restore_fullscreen_after_minimize:
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
            self.showNormal()

        QTimer.singleShot(120, self._aplicar_minimizado)

    def _aplicar_minimizado(self):
        self.setWindowState(Qt.WindowState.WindowMinimized)
        self.showMinimized()

    def iniciar_secuencia_burst(self):
        output_dir = Path(self.directorio)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.sequence_mgr = SequenceBurstManager(
            output_dir=str(output_dir),
            frame_count=130,
            exposure_time=8000.0,
            frame_rate=100.0,
            device_id=DEVICE_ID_DEFAULT,
        )
        self.sequence_mgr.status.connect(self.estado.setText)
        self.sequence_mgr.error.connect(self._on_sequence_error)
        self.sequence_mgr.burst_started.connect(self._on_burst_started)
        self.sequence_mgr.frames_captured.connect(self._on_frames_captured)
        self.sequence_mgr.burst_complete.connect(self._on_burst_complete)
        self.sequence_mgr.analysis_complete.connect(self._on_analysis_complete)
        self.sequence_mgr.temp_ready.connect(self.on_temp)
        self.sequence_mgr.stopped.connect(self._on_sequence_stopped)
        self.sequence_mgr.start()
        self.btn_run.setText(" Detener Analisis")
        self._set_operation_buttons_enabled(False)
        self.estado.setStyleSheet(
            "color: #4CAF50; font-size: 18px; font-weight: 600;"
        )

    def parar_secuencia_burst(self):
        manager = self.sequence_mgr
        self.sequence_mgr = None
        if manager is not None:
            manager.stop()
        self._on_sequence_stopped()

    def _on_sequence_error(self, msg):
        self._burst_processing_active = False
        logger.error("Error en secuencia: %s", msg)
        self.estado.setText(f"ERROR secuencia: {msg}")
        self.estado.setStyleSheet(
            "color: #FF5252; font-size: 18px; font-weight: bold;"
        )

    def _on_burst_started(self, count):
        self._burst_processing_active = True
        self.progress.setRange(0, count)
        self.progress.setValue(0)
        self.progress.show()

    def _on_frames_captured(self, current, total):
        self.progress.setValue(current)
        self.estado.setText(f"Capturando frame {current}/{total}...")

    def _on_burst_complete(self, save_dir, image_paths):
        self.progress.hide()
        self.estado.setText(
            f"Rafaga guardada: {len(image_paths)} imagenes. Analizando..."
        )

    def _on_analysis_complete(self, result):
        self._display_analysis_result(
            result,
            "Esperando siguiente trigger...",
        )
        self._burst_processing_active = False
        QTimer.singleShot(0, self.verificar_limite_rafagas)

    def _display_analysis_result(self, result, final_status):
        self.progress.hide()
        angle = result.exit_angle_deg
        self._last_result_path = result.diagnostic_path
        if result.diagnostic_path:
            item = result_item_for(result.diagnostic_path)
            self._set_main_pixmap(self.logo_label, item["result"])
            if item.get("frame"):
                self.result_frame_label.show()
                self._set_main_pixmap(self.result_frame_label, item["frame"])
            else:
                self.result_frame_label.hide()
                self.result_frame_label.clear()
        angle_text = f"{angle:.1f} grados" if angle is not None else "no detectado"
        self.estado.setText(
            f"Analisis terminado | Angulo: {angle_text} | "
            f"Frame de salida: {result.first_exit_frame or 'N/A'} | "
            f"{final_status}"
        )
        self.estado.setStyleSheet(
            "color: #4CAF50; font-size: 18px; font-weight: 600;"
        )

    def _set_main_pixmap(self, label, image_path):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            label.clear()
            return
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def analizar_rafaga_guardada(self):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar rafaga guardada",
            self.directorio,
            QFileDialog.Option.DontUseNativeDialog,
        )
        if not folder:
            return
        if not is_sequence_folder(folder):
            QMessageBox.warning(
                self,
                "Rafaga no valida",
                "La carpeta debe contener al menos dos imagenes img_*.bmp.",
            )
            return

        self.iniciar_analisis_rafaga_guardada(folder)

    def iniciar_analisis_rafaga_guardada(self, folder):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return
        if not is_sequence_folder(folder):
            QMessageBox.warning(
                self,
                "Rafaga no valida",
                "La carpeta debe contener al menos dos imagenes img_*.bmp.",
            )
            return

        self.progress.setRange(0, 0)
        self.progress.show()
        self._set_operation_buttons_enabled(False)
        self.estado.setText(f"Analizando rafaga guardada: {Path(folder).name}...")
        self.estado.setStyleSheet(
            "color: #4CAF50; font-size: 18px; font-weight: 600;"
        )

        thread = SavedSequenceAnalysisThread(folder, self)
        self.saved_analysis_thread = thread
        thread.result_ready.connect(self._on_saved_analysis_complete)
        thread.error.connect(self._on_saved_analysis_error)
        thread.finished.connect(self._on_saved_analysis_finished)
        thread.start()

    def _on_saved_analysis_complete(self, result):
        self._display_analysis_result(
            result,
            f"Rafaga guardada analizada: {Path(result.diagnostic_path).parent.name}",
        )

    def _on_saved_analysis_error(self, message):
        self.progress.hide()
        logger.error("Error analizando rafaga guardada: %s", message)
        self.estado.setText(f"ERROR analizando rafaga guardada: {message}")
        self.estado.setStyleSheet(
            "color: #FF5252; font-size: 18px; font-weight: bold;"
        )

    def _on_saved_analysis_finished(self):
        self.progress.hide()
        self._set_operation_buttons_enabled(True)
        thread = self.saved_analysis_thread
        self.saved_analysis_thread = None
        if thread is not None:
            thread.deleteLater()

    def _on_sequence_stopped(self):
        self._burst_processing_active = False
        self.btn_run.setText(" Ejecutar Analisis")
        self._set_operation_buttons_enabled(True)
        if self.sequence_mgr is not None and not self.sequence_mgr.running:
            self.sequence_mgr = None

    def _set_operation_buttons_enabled(self, enabled):
        for button in self._operation_buttons:
            button.setEnabled(enabled)
        if not self._is_admin:
            self.btn_delete_files.setEnabled(False)

    def _analysis_busy(self):
        return (
            self.sequence_mgr is not None and self.sequence_mgr.running
        ) or (
            self.saved_analysis_thread is not None
            and self.saved_analysis_thread.isRunning()
        )

    def operacion_en_ejecucion(self):
        return self._analysis_busy()

    def _warn_stop_analysis_first(self):
        QMessageBox.warning(
            self,
            "Operacion activa",
            "Detenga el analisis antes de realizar esta operacion.",
        )

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        value = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{size_bytes} B"

    def actualizar_barra_almacenamiento(self, current_size: int | None = None):
        if current_size is None:
            try:
                current_size = directory_size(self.directorio)
            except Exception as exc:
                logger.debug("No se pudo actualizar barra de almacenamiento: %s", exc)
                self.storage_label.setText("RAFAGAS: -- / 40.0 GB")
                self.storage_bar.setValue(0)
                return

        percent = min(100, int(round(current_size * 100 / DEFAULT_RESULTS_LIMIT_BYTES)))
        self.storage_bar.setValue(percent)
        self.storage_label.setText(
            f"RAFAGAS: {self._format_bytes(current_size)} / {self._format_bytes(DEFAULT_RESULTS_LIMIT_BYTES)}"
        )

        if percent >= 100:
            color = "#C62828"
        elif percent >= 85:
            color = "#F9A825"
        else:
            color = "#4CAF50"
        self.storage_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #2E7D32; background: #1A1A1A; border-radius: 3px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
        )

    def _retention_plan_txt_path(self) -> Path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path("/tmp") / f"AZA_rafagas_a_eliminar_{timestamp}.txt"

    def _write_retention_plan_txt(self, current_size: int, folders) -> Path:
        output_path = self._retention_plan_txt_path()
        total_to_delete = sum(folder.size_bytes for folder in folders)
        projected_size = max(0, current_size - total_to_delete)
        lines = [
            "LISTADO DE RAFAGAS PROPUESTAS PARA ELIMINAR",
            f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Directorio revisado: {self.directorio}",
            f"Limite permitido: {self._format_bytes(DEFAULT_RESULTS_LIMIT_BYTES)}",
            f"Uso actual: {self._format_bytes(current_size)}",
            f"Rafagas a eliminar: {len(folders)}",
            f"Espacio a liberar: {self._format_bytes(total_to_delete)}",
            f"Uso estimado despues de borrar: {self._format_bytes(projected_size)}",
            "",
            "RUTAS:",
            "",
        ]
        lines.extend(
            f"{index:04d}. {folder.path} | {self._format_bytes(folder.size_bytes)}"
            for index, folder in enumerate(folders, start=1)
        )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path

    def _confirm_retention_cleanup(self, current_size: int, folders) -> bool:
        plan_path = self._write_retention_plan_txt(current_size, folders)
        total_to_delete = sum(folder.size_bytes for folder in folders)
        projected_size = max(0, current_size - total_to_delete)

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Limite de almacenamiento de rafagas")
        dialog.setText(
            "La carpeta de rafagas supera el limite de 40.0 GB.\n\n"
            f"Uso actual: {self._format_bytes(current_size)}\n"
            f"Rafagas a eliminar: {len(folders)}\n"
            f"Espacio a liberar: {self._format_bytes(total_to_delete)}\n"
            f"Uso estimado despues: {self._format_bytes(projected_size)}\n\n"
            "El listado completo fue guardado en:\n"
            f"{plan_path}"
        )
        open_button = dialog.addButton("Ver listado TXT", QMessageBox.ButtonRole.ActionRole)
        delete_button = dialog.addButton("Eliminar rafagas", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = dialog.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)

        while True:
            dialog.exec()
            clicked = dialog.clickedButton()
            if clicked == open_button:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(plan_path)))
                continue
            if clicked == cancel_button:
                self.estado.setText("Limpieza de rafagas cancelada por el usuario.")
                return False
            if clicked == delete_button:
                confirm = QMessageBox.question(
                    self,
                    "Confirmar borrado",
                    "Esta accion no se puede deshacer.\n\n"
                    f"Se eliminaran {len(folders)} carpetas de rafagas.\n"
                    f"Listado completo:\n{plan_path}\n\n"
                    "Esta seguro que quiere eliminar estas rafagas?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if confirm == QMessageBox.StandardButton.Yes:
                    return True
                continue

    def verificar_limite_rafagas(self):
        if (
            self._retention_prompt_open
            or self._burst_processing_active
            or (
                self.saved_analysis_thread is not None
                and self.saved_analysis_thread.isRunning()
            )
            or not self.directorio
        ):
            return

        try:
            current_size, folders = cleanup_plan(self.directorio, DEFAULT_RESULTS_LIMIT_BYTES)
        except Exception as exc:
            logger.error("Error verificando limite de rafagas: %s", exc)
            return
        self.actualizar_barra_almacenamiento(current_size)
        if not folders:
            return

        self._retention_prompt_open = True
        try:
            if not self._confirm_retention_cleanup(current_size, folders):
                return

            deleted_bytes = delete_burst_folders(folders)
        except Exception as exc:
            logger.error("Error limpiando rafagas antiguas: %s", exc)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron borrar las rafagas antiguas:\n{exc}",
            )
            return
        finally:
            self._retention_prompt_open = False

        self.estado.setText(
            f"Limpieza completada. Espacio liberado: {self._format_bytes(deleted_bytes)}."
        )
        self.actualizar_barra_almacenamiento()

    def _result_images(self):
        if not self.directorio:
            return []
        return [
            result_item_for(path)
            for path in sorted(
                Path(self.directorio).rglob("resultado_analisis.png"),
                key=lambda path: (path.parent.name, path.stat().st_mtime),
            )
        ]

    def _image_files(self, directory):
        root = Path(directory)
        if not root.is_dir():
            return []
        return [
            str(path)
            for path in sorted(
                (
                    item
                    for item in root.rglob("*")
                    if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
                ),
                key=lambda path: (path.stat().st_mtime, str(path).lower()),
            )
        ]

    def ver_resultados(self):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return
        images = self._result_images()
        if not images:
            QMessageBox.information(
                self,
                "Resultados",
                f"No hay resultados guardados en:\n{self.directorio}",
            )
            return
        self.viewer = ResultViewer(images, start_index=len(images) - 1)
        self.viewer.showFullScreen()

    def abrir_carpeta_resultados(self):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return
        start_dir = self.directorio or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de imagenes",
            start_dir,
            QFileDialog.Option.DontUseNativeDialog,
        )
        if not folder:
            return

        images = self._image_files(folder)
        if not images:
            QMessageBox.information(
                self,
                "Imagenes",
                f"No hay imagenes en:\n{folder}",
            )
            return
        self.viewer = ResultViewer(images, start_index=len(images) - 1)
        self.viewer.showFullScreen()

    @staticmethod
    def _decode_mount_path(value: str) -> str:
        return (
            value.replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )

    def _external_storage_roots(self):
        mount_prefixes = (
            Path("/media"),
            Path("/run/media"),
            Path("/mnt"),
        )
        ignored_fs = {
            "autofs",
            "binfmt_misc",
            "bpf",
            "cgroup",
            "cgroup2",
            "configfs",
            "debugfs",
            "devpts",
            "devtmpfs",
            "efivarfs",
            "fusectl",
            "hugetlbfs",
            "mqueue",
            "overlay",
            "proc",
            "pstore",
            "securityfs",
            "sysfs",
            "tmpfs",
            "tracefs",
        }
        roots = []
        try:
            lines = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []

        for line in lines:
            parts = line.split()
            if len(parts) < 3 or parts[2] in ignored_fs:
                continue
            mount_path = Path(self._decode_mount_path(parts[1]))
            if not mount_path.is_dir():
                continue
            if any(mount_path == prefix or prefix in mount_path.parents for prefix in mount_prefixes):
                roots.append(mount_path)

        for prefix in mount_prefixes:
            if not prefix.is_dir():
                continue
            try:
                roots.extend(path for path in prefix.iterdir() if path.is_dir())
            except OSError:
                continue

        unique = []
        seen = set()
        for path in roots:
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            unique.append(path)
        return sorted(unique, key=lambda path: str(path).lower())

    def _select_download_destination(self):
        external_roots = self._external_storage_roots()
        start_dir = external_roots[0] if external_roots else Path("/media")

        dialog = QFileDialog(self, "Seleccionar almacenamiento externo")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setDirectory(str(start_dir))

        sidebar_paths = [
            Path.home(),
            Path.home() / "Desktop",
            Path(self.directorio),
            *external_roots,
            Path("/media"),
            Path("/run/media"),
            Path("/mnt"),
        ]
        sidebar_urls = [
            QUrl.fromLocalFile(str(path))
            for path in sidebar_paths
            if path.is_dir()
        ]
        if sidebar_urls:
            dialog.setSidebarUrls(sidebar_urls)

        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return None
        selected = dialog.selectedFiles()
        return selected[0] if selected else None

    def descargar_resultados(self):
        if self.sequence_mgr is not None and self.sequence_mgr.running:
            QMessageBox.warning(
                self,
                "Operacion activa",
                "Detenga el analisis por trigger antes de descargar resultados.",
            )
            return

        destination = self._select_download_destination()
        if not destination:
            return
        try:
            export_path = export_results(self.directorio, destination)
        except Exception as exc:
            logger.error("Error descargando resultados: %s", exc)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron descargar los resultados:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Descarga completada",
            f"Resultados descargados en:\n{export_path}",
        )

    def _select_delete_target(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Borrar")
        dialog.setText("Seleccione que desea borrar del directorio de resultados.")
        file_button = dialog.addButton("Archivo", QMessageBox.ButtonRole.AcceptRole)
        folder_button = dialog.addButton("Carpeta", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()

        clicked = dialog.clickedButton()
        start_dir = self.directorio or str(Path.home())
        if clicked == file_button:
            file_path, _selected_filter = QFileDialog.getOpenFileName(
                self,
                "Seleccionar archivo a borrar",
                start_dir,
                "Archivos (*)",
                options=QFileDialog.Option.DontUseNativeDialog,
            )
            return file_path or None
        if clicked == folder_button:
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Seleccionar carpeta a borrar",
                start_dir,
                QFileDialog.Option.DontUseNativeDialog,
            )
            return folder_path or None
        return None

    def borrar_archivo_o_carpeta(self):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return
        if not self._is_admin:
            QMessageBox.warning(self, "Acceso denegado", "Solo admin puede borrar archivos o carpetas.")
            return
        if not self.directorio:
            QMessageBox.warning(self, "Error", "Seleccione un directorio de resultados")
            return

        target = self._select_delete_target()
        if not target:
            return

        target_path = Path(target)
        resp = QMessageBox.question(
            self,
            "Confirmar borrado",
            f"¿Seguro que quieres borrar esta ruta?\n\n{target_path}\n\nEsta accion no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted_path = delete_result_path(self.directorio, target_path)
        except Exception as exc:
            logger.error("Error borrando ruta de resultados: %s", exc)
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo borrar la ruta seleccionada:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Borrado completado",
            f"Ruta borrada:\n{deleted_path}",
        )

    def on_temp(self, t):
        self.last_cam_temp = t

    def actualizar_barra_estado(self):
        now = datetime.datetime.now().timestamp()
        if now - self._last_storage_check >= 30:
            self._last_storage_check = now
            self.actualizar_barra_almacenamiento()

        connected = self.sequence_mgr is not None and self.sequence_mgr.running
        if connected:
            self.led_cam.setText(" NEOAPI EN OPERACION")
            self.led_cam.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 12px;")
        else:
            self.led_cam.setText(" NEOAPI EN ESPERA")
            self.led_cam.setStyleSheet("color: #9E9E9E; font-weight: bold; font-size: 12px;")

        t = self.last_cam_temp
        if t is None:
            self.val_temp.setText("TEMP: -- C")
            self.val_temp.setStyleSheet("color: #9E9E9E; font-weight: bold; font-size: 12px;")
        else:
            self.val_temp.setText(f"TEMP: {t:.1f} C")
            if t > 60.0:
                self.val_temp.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 12px;")
            else:
                self.val_temp.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")

    def toggle_menu(self):
        self.menu_visible = not self.menu_visible
        if self.menu_visible:
            self.side_menu.show()
            self.side_menu.move(0, 0)
        else:
            self.side_menu.hide()

    def seleccionar_directorio(self):
        if self._analysis_busy():
            self._warn_stop_analysis_first()
            return
        carpeta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta",
            "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if carpeta:
            self.directorio = carpeta
            self.estado.setText(f"Directorio de resultados: {carpeta}")

    def ejecutar_analisis(self):
        if not self.directorio:
            QMessageBox.warning(self, "Error", "Seleccione un directorio")
            return
        if self.sequence_mgr is not None and self.sequence_mgr.running:
            self.parar_secuencia_burst()
            self.estado.setText("Analisis detenido.")
            return
        self.iniciar_secuencia_burst()

    def analisis_en_ejecucion(self):
        return self.sequence_mgr is not None and self.sequence_mgr.running

    def closeEvent(self, event):
        try:
            if self.sequence_mgr is not None:
                self.sequence_mgr.stop()
                self.sequence_mgr = None
        except Exception:
            pass
        try:
            if (
                self.saved_analysis_thread is not None
                and self.saved_analysis_thread.isRunning()
            ):
                self.saved_analysis_thread.wait()
        except Exception:
            pass
        event.accept()
