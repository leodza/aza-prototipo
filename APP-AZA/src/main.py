# main.py - Entry point
import importlib.util
import os
import sys

os.environ.setdefault("GENICAM_GENTL64_PATH", "/opt/baumer-camera-explorer/lib")

# Allow both `python -m src.main` and `python src/main.py`.
if __package__ in {None, ""}:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_camera_runtime():
    """Reinicia con el entorno que contiene el SDK NeoAPI, si es necesario."""
    if importlib.util.find_spec("neoapi") is not None:
        return
    if os.environ.get("AZA_NEOAPI_REEXEC") == "1":
        return
    runtime = "/home/aza/miniconda3/envs/neoapi/bin/python"
    if not os.path.isfile(runtime):
        return
    os.environ["AZA_NEOAPI_REEXEC"] = "1"
    os.execv(runtime, [runtime, "-m", "src.main", *sys.argv[1:]])


_ensure_camera_runtime()

from PySide6.QtWidgets import QApplication

from src.core.config import (
    WEB_MONITOR_ENABLED,
    WEB_MONITOR_FPS,
    WEB_MONITOR_HOST,
    WEB_MONITOR_JPEG_QUALITY,
    WEB_MONITOR_PORT,
    WEB_MONITOR_SCREEN,
)
from src.core.logger import setup_logging
from src.database.models import inicializar_db
from src.ui.login import LoginDialog
from src.ui.app import AnalizadorApp
from src.web.monitor import ScreenWebMonitor

try:
    from src.ui.components import WelcomeScreen
    HAS_WELCOME = True
except ImportError:
    HAS_WELCOME = False


def main():
    setup_logging()

    app = QApplication(sys.argv)
    inicializar_db()

    dlg = LoginDialog()
    if not dlg.exec() or not dlg.operador:
        return 0

    main_win = AnalizadorApp(dlg.operador)
    web_monitor = None

    def handle_web_action(action: str):
        handlers = {
            "toggle_menu": main_win.toggle_menu,
            "analyze_saved": main_win.analizar_rafaga_guardada,
            "view_results": main_win.ver_resultados,
            "open_results": main_win.abrir_carpeta_resultados,
            "minimize": main_win.minimizar_ventana,
        }
        handler = handlers.get(action)
        if handler is not None:
            handler()

    def start_web_monitor():
        nonlocal web_monitor
        if web_monitor is not None or not WEB_MONITOR_ENABLED:
            return
        web_monitor = ScreenWebMonitor(
            host=WEB_MONITOR_HOST,
            port=WEB_MONITOR_PORT,
            screen_index=WEB_MONITOR_SCREEN,
            fps=WEB_MONITOR_FPS,
            jpeg_quality=WEB_MONITOR_JPEG_QUALITY,
            analysis_state=main_win.analisis_en_ejecucion,
            busy_state=main_win.operacion_en_ejecucion,
            results_root=lambda: main_win.directorio,
            source_widget=main_win,
            parent=app,
        )
        web_monitor.toggle_analysis_requested.connect(main_win.ejecutar_analisis)
        web_monitor.action_requested.connect(handle_web_action)
        web_monitor.saved_analysis_requested.connect(main_win.iniciar_analisis_rafaga_guardada)
        web_monitor.start()
        app.aboutToQuit.connect(web_monitor.stop)
        app._aza_web_monitor = web_monitor

    if HAS_WELCOME:
        main_win.hide()

        def start_main():
            main_win.showFullScreen()
            main_win.activateWindow()
            start_web_monitor()

        splash = WelcomeScreen(start_main)
        splash.show()
    else:
        main_win.showFullScreen()
        start_web_monitor()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
