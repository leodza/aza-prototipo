"""Monitor web para replicar pantalla y navegar resultados."""

from __future__ import annotations

import html
import json
import logging
import mimetypes
import socket
import subprocess
import threading
from io import BytesIO
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QRect, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from src.result_items import result_item_for

logger = logging.getLogger(__name__)

_BOUNDARY = b"aza-frame"

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a runtime dependency.
    Image = None

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - OpenCV is a runtime dependency.
    cv2 = None
    np = None


def _stretch_for_display(image):
    """Ajusta contraste para que capturas Bayer oscuras sean visibles en web."""
    if np is None:
        return image
    source = image.astype(np.float32)
    low, high = np.percentile(source, (1, 99.7))
    if high <= low:
        low = float(source.min())
        high = float(source.max())
    if high <= low:
        return image
    stretched = (source - low) * (255.0 / (high - low))
    return np.clip(stretched, 0, 255).astype(np.uint8)


class FrameStore:
    """Almacena el ultimo JPEG y notifica a los clientes del stream."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._frame = b""
        self._sequence = 0

    def update(self, frame: bytes) -> None:
        if not frame:
            return
        with self._condition:
            self._frame = frame
            self._sequence += 1
            self._condition.notify_all()

    def latest(self) -> tuple[bytes, int]:
        with self._condition:
            return self._frame, self._sequence

    def wait_for_next(self, sequence: int, timeout: float = 2.0) -> tuple[bytes, int]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._sequence != sequence,
                timeout=timeout,
            )
            return self._frame, self._sequence


IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
DEFAULT_RESULTS_DIR = Path.home() / "Desktop" / "RESULTADOS_ANALISIS_SALIDA_ROLLO"


def _viewer_page(title: str) -> bytes:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; margin: 0; background: #090909; }}
    body {{
      color: #f4f4f4;
      font-family: Arial, Helvetica, sans-serif;
      overflow: hidden;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 260px 1fr;
      width: 100%;
      height: 100%;
      min-width: 0;
    }}
    .toolbar {{
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 15px;
      min-width: 0;
      padding: 30px;
      background: #1b5e20;
      border-right: 1px solid #2e7d32;
    }}
    .toolbar-title {{
      color: #fff;
      font-size: 16px;
      font-weight: 700;
      margin-bottom: 2px;
    }}
    .actions {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
      overflow: visible;
    }}
    button {{
      width: 100%;
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: #4caf50;
      color: #fff;
      font-weight: 700;
      font-family: Arial, Helvetica, sans-serif;
      cursor: pointer;
      white-space: nowrap;
      text-align: left;
      padding: 8px 12px;
    }}
    button:hover {{ background: #388e3c; }}
    button.secondary {{ background: #333; }}
    button.secondary:hover {{ background: #424242; }}
    button.danger {{ background: #c62828; }}
    button.danger:hover {{ background: #b71c1c; }}
    button:disabled {{
      background: #2e7d32;
      color: #c8e6c9;
      cursor: not-allowed;
      opacity: 0.65;
    }}
    .viewer {{
      position: relative;
      min-width: 0;
      min-height: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #050505;
    }}
    #monitor {{
      position: absolute;
      inset: 0;
      display: block;
      width: 100%;
      height: 100%;
      max-width: none;
      max-height: none;
      object-fit: contain;
      user-select: none;
      -webkit-user-drag: none;
    }}
    .status {{
      margin-top: auto;
      overflow: hidden;
      color: rgba(255,255,255,0.78);
      font-size: 12px;
      font-weight: 700;
      text-align: left;
      text-overflow: ellipsis;
      line-height: 1.35;
    }}
    .panel {{
      position: absolute;
      inset: 24px;
      display: none;
      grid-template-rows: auto 1fr;
      min-width: 0;
      min-height: 0;
      background: #101010;
      border: 1px solid #2e7d32;
      box-shadow: 0 12px 36px rgba(0,0,0,0.55);
      z-index: 2;
    }}
    .panel.open {{ display: grid; }}
    .panel-head {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      background: #0a2e0d;
      border-bottom: 1px solid #2e7d32;
    }}
    .panel-head button {{
      width: auto;
      min-width: 78px;
      min-height: 34px;
      padding: 6px 10px;
      text-align: center;
    }}
    .panel-title {{
      flex: 1 1 auto;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
    }}
    .panel-body {{
      min-width: 0;
      min-height: 0;
      overflow: hidden;
    }}
    .image-stage {{
      position: relative;
      width: 100%;
      height: 100%;
      background: #000;
    }}
    .image-stage img {{
      position: absolute;
      inset: 50%;
      width: 92%;
      height: 92%;
      transform: translate(-50%, -50%);
      object-fit: contain;
    }}
    .image-stage img:not([src]) {{ display: none; }}
    .comparison-stage {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      background: #000;
    }}
    .comparison-stage img {{
      position: static;
      width: 100%;
      height: 100%;
      transform: none;
      object-fit: contain;
      min-width: 0;
      min-height: 0;
    }}
    .comparison-stage.single {{
      display: block;
      position: relative;
    }}
    .comparison-stage.single img {{
      position: absolute;
      inset: 50%;
      width: 92%;
      height: 92%;
      transform: translate(-50%, -50%);
    }}
    .nav-arrow {{
      position: absolute;
      top: 0;
      bottom: 0;
      width: 74px;
      border-radius: 0;
      text-align: center;
      font-size: 42px;
      background: rgba(27,94,32,0.82);
      z-index: 3;
    }}
    .nav-arrow.prev {{ left: 0; }}
    .nav-arrow.next {{ right: 0; }}
    .browser-grid {{
      display: grid;
      grid-template-columns: 330px 1fr;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }}
    .browser-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-height: 0;
      overflow: auto;
      padding: 12px;
      background: #151515;
      border-right: 1px solid #2b2b2b;
    }}
    .entry {{
      min-height: 38px;
      border: 1px solid #2d2d2d;
      background: #202020;
      color: #fff;
      text-align: left;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .entry:hover {{ border-color: #4caf50; }}
    @media (max-width: 900px) {{
      .shell {{ grid-template-columns: 1fr; grid-template-rows: auto 1fr; }}
      .toolbar {{ border-right: 0; border-bottom: 1px solid #2e7d32; padding: 14px; }}
      .actions {{ flex-direction: row; overflow-x: auto; }}
      button {{ width: auto; min-width: max-content; }}
      .panel {{ inset: 8px; }}
      .browser-grid {{ grid-template-columns: 1fr; grid-template-rows: 260px 1fr; }}
      .browser-list {{ border-right: 0; border-bottom: 1px solid #2b2b2b; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="toolbar">
      <div class="toolbar-title">AZA Web</div>
      <div class="actions">
        <button data-action="toggle_menu" class="secondary">Menu</button>
        <button data-action="select_directory" disabled title="Disponible solo en Qt">Seleccionar Directorio</button>
        <button data-action="toggle_analysis" id="analysisButton">Ejecutar Analisis</button>
        <button data-action="analyze_saved">Analizar Rafaga Guardada</button>
        <button data-action="view_results">Ver Resultados</button>
        <button data-action="open_results">Abrir Carpeta Resultados</button>
        <button data-action="download" disabled title="Disponible solo en Qt">Descargar</button>
        <button data-action="minimize" class="secondary">Minimizar</button>
      </div>
      <div class="status" id="status">Monitor en vivo</div>
    </aside>
    <main class="viewer">
      <img id="monitor" src="/stream.mjpg" alt="Monitor AZA">
      <section class="panel" id="imagePanel">
        <div class="panel-head">
          <div class="panel-title" id="imageTitle">Resultados</div>
          <button class="secondary" id="closeImagePanel">Volver</button>
        </div>
        <div class="panel-body">
          <div class="image-stage">
          <button class="nav-arrow prev" id="prevImage">&lt;</button>
          <div class="comparison-stage single" id="resultStage">
            <img id="panelImage" alt="">
            <img id="panelFrameImage" alt="">
          </div>
          <button class="nav-arrow next" id="nextImage">&gt;</button>
          </div>
        </div>
      </section>
      <section class="panel" id="browserPanel">
        <div class="panel-head">
          <button class="secondary" id="upFolder">Subir</button>
          <button id="analyzeFolder">Analizar esta carpeta</button>
          <div class="panel-title" id="browserTitle">Carpetas</div>
          <button class="secondary" id="closeBrowserPanel">Volver</button>
        </div>
        <div class="panel-body browser-grid">
          <div class="browser-list" id="browserList"></div>
          <div class="image-stage">
            <button class="nav-arrow prev" id="prevBrowserImage">&lt;</button>
            <img id="browserImage" alt="">
            <button class="nav-arrow next" id="nextBrowserImage">&gt;</button>
          </div>
        </div>
      </section>
    </main>
  </div>
  <script>
    const statusEl = document.getElementById('status');
    const analysisButton = document.getElementById('analysisButton');
    const imagePanel = document.getElementById('imagePanel');
    const imageTitle = document.getElementById('imageTitle');
    const panelImage = document.getElementById('panelImage');
    const panelFrameImage = document.getElementById('panelFrameImage');
    const resultStage = document.getElementById('resultStage');
    const browserPanel = document.getElementById('browserPanel');
    const browserTitle = document.getElementById('browserTitle');
    const browserList = document.getElementById('browserList');
    const browserImage = document.getElementById('browserImage');
    let resultImages = [];
    let resultIndex = 0;
    let browserImages = [];
    let browserIndex = 0;
    let browserParent = '';
    let browserRoots = [];
    let browserPath = '';
    let browserMode = 'browse';
    let appBusy = false;

    function qs(path) {{ return encodeURIComponent(path); }}
    function imageUrl(path) {{ return '/file?path=' + qs(path); }}
    function basename(path) {{ return path.split('/').filter(Boolean).pop() || path; }}
    function showPanel(panel) {{
      imagePanel.classList.remove('open');
      browserPanel.classList.remove('open');
      panel.classList.add('open');
    }}
    function showResultImage() {{
      if (!resultImages.length) return;
      const item = resultImages[resultIndex];
      const path = typeof item === 'string' ? item : item.result;
      const frame = typeof item === 'string' ? null : item.frame;
      panelImage.src = imageUrl(path);
      if (frame) {{
        panelFrameImage.src = imageUrl(frame);
        resultStage.classList.remove('single');
      }} else {{
        panelFrameImage.removeAttribute('src');
        resultStage.classList.add('single');
      }}
      imageTitle.textContent = `${{basename(path)}} (${{resultIndex + 1}}/${{resultImages.length}})`;
    }}
    async function openLatestResults() {{
      statusEl.textContent = 'Cargando resultados...';
      const response = await fetch('/api/results', {{cache: 'no-store'}});
      if (!response.ok) throw new Error('results failed');
      const data = await response.json();
      resultImages = data.items || data.images || [];
      if (!resultImages.length) {{
        statusEl.textContent = 'No hay resultados guardados';
        return;
      }}
      resultIndex = resultImages.length - 1;
      showResultImage();
      showPanel(imagePanel);
      statusEl.textContent = 'Resultados';
    }}
    function moveResult(delta) {{
      if (!resultImages.length) return;
      resultIndex = Math.max(0, Math.min(resultImages.length - 1, resultIndex + delta));
      showResultImage();
    }}
    function showBrowserImage() {{
      if (!browserImages.length) {{
        browserImage.removeAttribute('src');
        return;
      }}
      const item = browserImages[browserIndex];
      browserImage.src = imageUrl(item.path);
      browserTitle.textContent = `${{basename(item.path)}} (${{browserIndex + 1}}/${{browserImages.length}})`;
    }}
    function moveBrowserImage(delta) {{
      if (!browserImages.length) return;
      browserIndex = Math.max(0, Math.min(browserImages.length - 1, browserIndex + delta));
      showBrowserImage();
    }}
    function entryButton(item) {{
      const button = document.createElement('button');
      button.className = 'entry';
      button.textContent = `${{item.type === 'dir' ? '[DIR]' : '[IMG]'}} ${{item.name}}`;
      button.onclick = () => {{
        if (item.type === 'dir') {{
          loadDirectory(item.path);
        }} else {{
          const index = browserImages.findIndex(image => image.path === item.path);
          if (index >= 0) {{
            browserIndex = index;
            showBrowserImage();
          }}
        }}
      }};
      return button;
    }}
    function showRoots() {{
      browserParent = '';
      browserPath = '';
      browserImages = [];
      browserImage.removeAttribute('src');
      browserTitle.textContent = 'Ubicaciones';
      document.getElementById('analyzeFolder').style.display = browserMode === 'analyze' ? 'inline-block' : 'none';
      browserList.textContent = '';
      browserRoots.forEach(root => {{
        browserList.appendChild(entryButton({{
          type: 'dir',
          name: root.label,
          path: root.path
        }}));
      }});
      if (!browserRoots.length) browserList.textContent = 'Sin ubicaciones disponibles.';
      showPanel(browserPanel);
    }}
    async function loadDirectory(path) {{
      const response = await fetch('/api/list?path=' + qs(path), {{cache: 'no-store'}});
      if (!response.ok) throw new Error('list failed');
      const data = await response.json();
      browserPath = data.path;
      browserParent = data.parent || '';
      browserTitle.textContent = data.path;
      document.getElementById('analyzeFolder').style.display = browserMode === 'analyze' ? 'inline-block' : 'none';
      browserList.textContent = '';
      browserImages = data.entries.filter(item => item.type === 'image');
      browserIndex = browserImages.length ? browserImages.length - 1 : 0;
      data.entries.forEach(item => browserList.appendChild(entryButton(item)));
      if (!data.entries.length) browserList.textContent = 'Sin subcarpetas ni imagenes.';
      showBrowserImage();
      showPanel(browserPanel);
    }}
    async function openFolderBrowser(mode='browse') {{
      browserMode = mode;
      statusEl.textContent = 'Cargando carpetas...';
      const response = await fetch('/api/roots', {{cache: 'no-store'}});
      if (!response.ok) throw new Error('roots failed');
      const data = await response.json();
      browserRoots = data.roots || [];
      showRoots();
      statusEl.textContent = 'Explorador de imagenes';
    }}
    async function updateAnalysisState() {{
      const response = await fetch('/api/analysis-state', {{cache: 'no-store'}});
      if (!response.ok) return;
      const data = await response.json();
      appBusy = Boolean(data.busy || data.running);
      analysisButton.textContent = data.running ? 'Detener Analisis' : 'Ejecutar Analisis';
      document.querySelectorAll('[data-action="analyze_saved"], [data-action="view_results"], [data-action="open_results"]').forEach(button => {{
        button.disabled = appBusy;
        button.title = appBusy ? 'Detenga el analisis antes de realizar esta operacion' : '';
      }});
    }}
    async function sendAction(action, button) {{
      if (button.disabled) return;
      if (appBusy && ['analyze_saved', 'view_results', 'open_results'].includes(action)) {{
        statusEl.textContent = 'Detenga el analisis antes de realizar esta operacion';
        return;
      }}
      if (action === 'analyze_saved') {{
        openFolderBrowser('analyze').catch(() => {{ statusEl.textContent = 'No se pudo abrir el explorador'; }});
        return;
      }}
      if (action === 'view_results') {{
        openLatestResults().catch(() => {{ statusEl.textContent = 'No se pudieron cargar resultados'; }});
        return;
      }}
      if (action === 'open_results') {{
        openFolderBrowser('browse').catch(() => {{ statusEl.textContent = 'No se pudo abrir el explorador'; }});
        return;
      }}
      button.disabled = true;
      statusEl.textContent = 'Enviando comando...';
      try {{
        const response = await fetch('/api/action?action=' + encodeURIComponent(action), {{
          method: 'POST',
          cache: 'no-store'
        }});
        if (!response.ok) {{
          const text = await response.text();
          throw new Error(text || 'request failed');
        }}
        await updateAnalysisState();
        statusEl.textContent = 'Comando enviado';
      }} catch (err) {{
        statusEl.textContent = 'No se pudo ejecutar el comando';
      }} finally {{
        button.disabled = false;
      }}
    }}
    document.querySelectorAll('button[data-action]').forEach(button => {{
      button.addEventListener('click', () => sendAction(button.dataset.action, button));
    }});
    document.getElementById('closeImagePanel').onclick = () => imagePanel.classList.remove('open');
    document.getElementById('prevImage').onclick = () => moveResult(-1);
    document.getElementById('nextImage').onclick = () => moveResult(1);
    document.getElementById('closeBrowserPanel').onclick = () => browserPanel.classList.remove('open');
    document.getElementById('analyzeFolder').onclick = async () => {{
      if (!browserPath) {{
        statusEl.textContent = 'Seleccione una carpeta de rafaga';
        return;
      }}
      try {{
        const response = await fetch('/api/analyze-saved?path=' + qs(browserPath), {{
          method: 'POST',
          cache: 'no-store'
        }});
        if (!response.ok) throw new Error('analyze failed');
        browserPanel.classList.remove('open');
        statusEl.textContent = 'Analisis de rafaga iniciado';
        await updateAnalysisState();
      }} catch (err) {{
        statusEl.textContent = 'La carpeta no es una rafaga valida';
      }}
    }};
    document.getElementById('upFolder').onclick = () => {{
      if (browserParent) {{
        loadDirectory(browserParent).catch(() => {{}});
      }} else {{
        showRoots();
      }}
    }};
    document.getElementById('prevBrowserImage').onclick = () => moveBrowserImage(-1);
    document.getElementById('nextBrowserImage').onclick = () => moveBrowserImage(1);
    updateAnalysisState().catch(() => {{}});
    setInterval(() => updateAnalysisState().catch(() => {{}}), 2000);
  </script>
</body>
</html>
""".encode("utf-8")


class MonitorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        frame_store: FrameStore,
        title: str = "AZA Monitor",
        results_root: str | Path | None = None,
        results_root_getter: Callable[[], str | Path] | None = None,
        busy_state: Callable[[], bool] | None = None,
        saved_analysis_callback: Callable[[str], None] | None = None,
        analysis_toggle: Callable[[], None] | None = None,
        analysis_state: Callable[[], bool] | None = None,
        action_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.frame_store = frame_store
        self.viewer_page = _viewer_page(title)
        self.results_root = Path(results_root or DEFAULT_RESULTS_DIR).expanduser()
        self.results_root_getter = results_root_getter
        self.busy_state = busy_state
        self.saved_analysis_callback = saved_analysis_callback
        self.analysis_toggle = analysis_toggle
        self.analysis_state = analysis_state
        self.action_callback = action_callback
        self.allowed_roots = self._build_allowed_roots()
        super().__init__(server_address, MonitorRequestHandler)

    def current_results_root(self) -> Path:
        if self.results_root_getter is None:
            return self.results_root
        try:
            return Path(self.results_root_getter()).expanduser()
        except Exception:
            logger.exception("No se pudo leer directorio actual de resultados")
            return self.results_root

    def is_busy(self) -> bool:
        if self.busy_state is None:
            if self.analysis_state is None:
                return False
            try:
                return bool(self.analysis_state())
            except Exception:
                logger.exception("No se pudo leer estado de analisis")
                return False
        try:
            return bool(self.busy_state())
        except Exception:
            logger.exception("No se pudo leer estado ocupado")
            return False

    def _build_allowed_roots(self) -> list[Path]:
        candidates = [
            self.results_root,
            self.results_root.parent,
            Path.home(),
            Path.home() / "Desktop",
            Path("/media"),
            Path("/run/media"),
            Path("/mnt"),
        ]
        roots = []
        seen = set()
        for candidate in candidates:
            try:
                resolved = candidate.expanduser().resolve()
            except OSError:
                resolved = candidate.expanduser().absolute()
            if str(resolved) in seen:
                continue
            seen.add(str(resolved))
            roots.append(resolved)
        return roots

    def is_allowed_path(self, path: Path) -> bool:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            resolved = path.expanduser().absolute()
        for root in self.allowed_roots:
            if resolved == root or root in resolved.parents:
                return True
        return False

    def external_roots(self) -> list[Path]:
        roots = []
        for base in (Path("/media"), Path("/run/media"), Path("/mnt")):
            if not base.is_dir():
                continue
            try:
                roots.extend(path for path in base.iterdir() if path.is_dir())
            except OSError:
                continue
        unique = []
        seen = set()
        for path in roots:
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path.absolute()
            if str(resolved) in seen:
                continue
            seen.add(str(resolved))
            unique.append(resolved)
        return sorted(unique, key=lambda item: str(item).lower())


class MonitorRequestHandler(BaseHTTPRequestHandler):
    server: MonitorHTTPServer

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/toggle-analysis":
            self._toggle_analysis()
            return
        if parsed.path == "/api/action":
            self._run_action(parsed.query)
            return
        if parsed.path == "/api/analyze-saved":
            self._analyze_saved(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_IMPLEMENTED)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._send_index()
        elif path == "/stream.mjpg":
            self._send_stream()
        elif path == "/snapshot.jpg":
            self._send_snapshot()
        elif path == "/health":
            self._send_health()
        elif path == "/api/roots":
            self._send_roots()
        elif path == "/api/list":
            self._send_directory(parsed.query)
        elif path == "/api/results":
            self._send_results()
        elif path == "/api/analysis-state":
            self._send_analysis_state()
        elif path == "/file":
            self._send_file(parsed.query)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _json_response(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _query_path(self, query: str) -> Path | None:
        values = parse_qs(query).get("path")
        if not values:
            return None
        return Path(unquote(values[0])).expanduser()

    @staticmethod
    def _root_label(path: Path) -> str:
        home = Path.home()
        if path == home:
            return "Inicio"
        if path == home / "Desktop":
            return "Escritorio"
        if path.name:
            return path.name
        return str(path)

    def _send_roots(self) -> None:
        if self.server.is_busy():
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de navegar archivos",
            )
            return
        roots = []
        seen = set()
        for path in [*self.server.allowed_roots, *self.server.external_roots()]:
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path.absolute()
            if str(resolved) in seen:
                continue
            seen.add(str(resolved))
            roots.append(
                {
                    "label": self._root_label(resolved),
                    "path": str(resolved),
                }
            )

        self._json_response(
            {
                "start": str(self.server.current_results_root()),
                "roots": roots,
            }
        )

    def _send_analysis_state(self) -> None:
        running = False
        if self.server.analysis_state is not None:
            try:
                running = bool(self.server.analysis_state())
            except Exception:
                logger.exception("No se pudo leer estado de analisis")
        self._json_response({"running": running, "busy": running or self.server.is_busy()})

    def _toggle_analysis(self) -> None:
        if self.server.analysis_toggle is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Control no disponible")
            return
        try:
            self.server.analysis_toggle()
        except Exception as exc:
            logger.exception("No se pudo ejecutar comando de analisis")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return
        self._json_response({"accepted": True})

    def _run_action(self, query: str) -> None:
        action = parse_qs(query).get("action", [""])[0]
        if action in {"select_directory", "download"}:
            self.send_error(
                HTTPStatus.FORBIDDEN,
                "Accion disponible solo en la aplicacion Qt",
            )
            return
        if action == "toggle_analysis":
            self._toggle_analysis()
            return
        allowed = {
            "toggle_menu",
            "view_results",
            "open_results",
            "minimize",
        }
        if action not in allowed:
            self.send_error(HTTPStatus.BAD_REQUEST, "Accion no valida")
            return
        if self.server.is_busy() and action in {"analyze_saved", "view_results", "open_results"}:
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de realizar esta operacion",
            )
            return
        if self.server.action_callback is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Control no disponible")
            return
        try:
            self.server.action_callback(action)
        except Exception as exc:
            logger.exception("No se pudo ejecutar accion web: %s", action)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return
        self._json_response({"accepted": True, "action": action})

    @staticmethod
    def _is_sequence_folder(path: Path) -> bool:
        try:
            return sum(1 for item in path.glob("img_*.bmp") if item.is_file()) >= 2
        except OSError:
            return False

    def _analyze_saved(self, query: str) -> None:
        if self.server.is_busy():
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de realizar esta operacion",
            )
            return
        folder = self._query_path(query)
        if folder is None:
            self.send_error(HTTPStatus.BAD_REQUEST, "Falta path")
            return
        if not self.server.is_allowed_path(folder):
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return
        try:
            resolved = folder.resolve()
        except OSError:
            resolved = folder.absolute()
        if not resolved.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND, "Carpeta no encontrada")
            return
        if not self._is_sequence_folder(resolved):
            self.send_error(
                HTTPStatus.BAD_REQUEST,
                "La carpeta debe contener al menos dos imagenes img_*.bmp",
            )
            return
        if self.server.saved_analysis_callback is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Control no disponible")
            return
        try:
            self.server.saved_analysis_callback(str(resolved))
        except Exception as exc:
            logger.exception("No se pudo iniciar analisis de rafaga guardada")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return
        self._json_response({"accepted": True, "path": str(resolved)})

    def _send_results(self) -> None:
        if self.server.is_busy():
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de ver resultados",
            )
            return
        root = self.server.current_results_root()
        images = []
        if root.is_dir():
            try:
                result_paths = [
                    path
                    for path in sorted(
                        root.rglob("resultado_analisis.png"),
                        key=lambda item: (item.stat().st_mtime, str(item).lower()),
                    )
                    if self.server.is_allowed_path(path)
                ]
                images = [str(path) for path in result_paths]
                items = [result_item_for(path) for path in result_paths]
            except OSError:
                images = []
                items = []
        else:
            items = []
        self._json_response({"images": images, "items": items})

    def _send_directory(self, query: str) -> None:
        if self.server.is_busy():
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de navegar archivos",
            )
            return
        directory = self._query_path(query)
        if directory is None:
            self.send_error(HTTPStatus.BAD_REQUEST, "Falta path")
            return
        if not self.server.is_allowed_path(directory):
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return

        try:
            resolved = directory.resolve()
        except OSError:
            resolved = directory.absolute()
        if not resolved.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND, "Carpeta no encontrada")
            return

        entries = []
        try:
            children = sorted(
                resolved.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )
        except OSError as exc:
            self.send_error(HTTPStatus.FORBIDDEN, str(exc))
            return

        for child in children:
            if child.name.startswith("."):
                continue
            if child.is_dir():
                entries.append(
                    {
                        "type": "dir",
                        "name": child.name,
                        "path": str(child),
                    }
                )
            elif child.is_file() and child.suffix.lower() in IMAGE_SUFFIXES:
                entries.append(
                    {
                        "type": "image",
                        "name": child.name,
                        "path": str(child),
                    }
                )

        parent = resolved.parent if resolved.parent != resolved else None
        if parent is not None and not self.server.is_allowed_path(parent):
            parent = None
        self._json_response(
            {
                "path": str(resolved),
                "parent": str(parent) if parent is not None else "",
                "entries": entries,
            }
        )

    def _send_file(self, query: str) -> None:
        if self.server.is_busy():
            self.send_error(
                HTTPStatus.CONFLICT,
                "Detenga el analisis antes de ver imagenes",
            )
            return
        file_path = self._query_path(query)
        if file_path is None:
            self.send_error(HTTPStatus.BAD_REQUEST, "Falta path")
            return
        if not self.server.is_allowed_path(file_path):
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return

        try:
            resolved = file_path.resolve()
        except OSError:
            resolved = file_path.absolute()
        if not resolved.is_file() or resolved.suffix.lower() not in IMAGE_SUFFIXES:
            self.send_error(HTTPStatus.NOT_FOUND, "Imagen no encontrada")
            return

        try:
            body, content_type = self._display_image_bytes(resolved)
        except OSError as exc:
            self.send_error(HTTPStatus.FORBIDDEN, str(exc))
            return
        except Exception as exc:
            logger.exception("No se pudo preparar imagen para web: %s", resolved)
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _display_image_bytes(path: Path) -> tuple[bytes, str]:
        if path.suffix.lower() == ".bmp" and cv2 is not None and np is not None:
            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if image is None:
                raise OSError(f"No se pudo leer {path}")
            if image.ndim == 2:
                if image.shape[0] >= 4 and image.shape[1] >= 4:
                    image = cv2.cvtColor(image, cv2.COLOR_BAYER_RG2RGB)
                else:
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.ndim == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = _stretch_for_display(image)
            ok, encoded = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            if not ok:
                raise OSError(f"No se pudo codificar {path}")
            return encoded.tobytes(), "image/png"

        if path.suffix.lower() == ".bmp" and Image is not None:
            with Image.open(path) as image:
                output = BytesIO()
                image.save(output, format="PNG")
                return output.getvalue(), "image/png"

        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        return path.read_bytes(), content_type

    def _send_index(self) -> None:
        body = self.server.viewer_page
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_snapshot(self) -> None:
        frame, _ = self.server.frame_store.latest()
        if not frame:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Captura aun no disponible")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(frame)

    def _send_health(self) -> None:
        frame, sequence = self.server.frame_store.latest()
        body = (
            f'{{"status":"{"ok" if frame else "starting"}","frame":{sequence}}}'
        ).encode("ascii")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode('ascii')}",
        )
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        sequence = -1
        try:
            while True:
                frame, next_sequence = self.server.frame_store.wait_for_next(sequence)
                if not frame or next_sequence == sequence:
                    continue
                sequence = next_sequence
                self.wfile.write(b"--" + _BOUNDARY + b"\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(
                    f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                )
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def log_message(self, format: str, *args: object) -> None:
        logger.debug("Monitor web %s - %s", self.client_address[0], format % args)


def lan_urls(port: int) -> list[str]:
    """Devuelve URLs candidatas accesibles desde la red local."""
    addresses: set[str] = set()

    try:
        result = subprocess.run(
            ["hostname", "-I"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
        for value in result.stdout.split():
            try:
                socket.inet_aton(value)
            except OSError:
                continue
            if not value.startswith(("127.", "169.254.")):
                addresses.add(value)
    except (OSError, subprocess.SubprocessError):
        pass

    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith(("127.", "169.254.")):
                addresses.add(address)
    except socket.gaierror:
        pass

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("10.255.255.255", 1))
            address = probe.getsockname()[0]
            if not address.startswith(("127.", "169.254.")):
                addresses.add(address)
        finally:
            probe.close()
    except OSError:
        pass

    return [f"http://{address}:{port}" for address in sorted(addresses)]


class ScreenWebMonitor(QObject):
    """Captura una QScreen en el hilo Qt y publica el ultimo frame por HTTP."""

    toggle_analysis_requested = Signal()
    action_requested = Signal(str)
    saved_analysis_requested = Signal(str)

    def __init__(
        self,
        host: str,
        port: int,
        screen_index: int = 0,
        fps: int = 5,
        jpeg_quality: int = 70,
        analysis_state: Callable[[], bool] | None = None,
        busy_state: Callable[[], bool] | None = None,
        results_root: Callable[[], str | Path] | None = None,
        source_widget: QWidget | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.host = host
        self.port = port
        self.screen_index = screen_index
        self.fps = max(1, min(fps, 30))
        self.jpeg_quality = max(20, min(jpeg_quality, 95))
        self.analysis_state = analysis_state
        self.busy_state = busy_state
        self.results_root = results_root
        self.source_widget = source_widget
        self.frame_store = FrameStore()
        self._server: MonitorHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.capture_frame)

    def start(self) -> bool:
        if self._server is not None:
            return True
        try:
            self._server = MonitorHTTPServer(
                (self.host, self.port),
                self.frame_store,
                results_root_getter=self.results_root,
                busy_state=self.busy_state,
                saved_analysis_callback=self.saved_analysis_requested.emit,
                analysis_toggle=self.toggle_analysis_requested.emit,
                analysis_state=self.analysis_state,
                action_callback=self.action_requested.emit,
            )
        except OSError as exc:
            logger.error(
                "No se pudo iniciar el monitor web en %s:%s: %s",
                self.host,
                self.port,
                exc,
            )
            return False

        self.port = self._server.server_address[1]
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="aza-web-monitor",
            daemon=True,
        )
        self._server_thread.start()
        self._timer.start(round(1000 / self.fps))
        QTimer.singleShot(0, self.capture_frame)

        urls = lan_urls(self.port)
        logger.info(
            "Monitor web de solo lectura disponible en %s",
            ", ".join(urls) if urls else f"http://127.0.0.1:{self.port}",
        )
        return True

    def capture_frame(self) -> None:
        pixmap = self._capture_qt_windows()
        if pixmap is None or pixmap.isNull():
            return

        data = QByteArray()
        buffer = QBuffer(data)
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            return
        try:
            if pixmap.save(buffer, "JPEG", self.jpeg_quality):
                self.frame_store.update(bytes(data))
        finally:
            buffer.close()

    def _capture_qt_windows(self) -> QPixmap | None:
        """Captura solo ventanas Qt de la app, no todo el escritorio."""
        screens = QGuiApplication.screens()
        if not screens:
            return None
        index = min(max(self.screen_index, 0), len(screens) - 1)
        target_screen = screens[index]

        primary = self.source_widget
        if primary is not None:
            size = primary.size()
            if size.isValid() and not size.isEmpty():
                widgets = [(primary, QRect(0, 0, size.width(), size.height()))]
            else:
                widgets = []
        else:
            widgets = []

        for widget in QApplication.topLevelWidgets():
            if widget is primary:
                continue
            if not widget.isVisible() or widget.isMinimized():
                continue
            window = widget.windowHandle()
            if window is not None and window.screen() is not target_screen:
                continue
            geometry = widget.frameGeometry()
            if geometry.isEmpty():
                continue
            widgets.append((widget, geometry))

        if not widgets:
            return None

        active = QApplication.activeWindow()
        widgets.sort(key=lambda item: item[0] is active)

        bounds = QRect(widgets[0][1])
        for _, geometry in widgets[1:]:
            bounds = bounds.united(geometry)

        canvas = QPixmap(bounds.size())
        canvas.fill(QColor("#050505"))
        painter = QPainter(canvas)
        try:
            for widget, geometry in widgets:
                window_pixmap = widget.grab()
                if window_pixmap.isNull():
                    continue
                target = QRect(geometry.topLeft() - bounds.topLeft(), geometry.size())
                painter.drawPixmap(target, window_pixmap)
        finally:
            painter.end()

        return canvas

    def stop(self) -> None:
        self._timer.stop()
        server = self._server
        thread = self._server_thread
        self._server = None
        self._server_thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
