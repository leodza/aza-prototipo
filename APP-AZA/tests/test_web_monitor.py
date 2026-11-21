import threading
import urllib.parse
import urllib.error
import urllib.request

from PIL import Image, ImageStat

from src.web.monitor import FrameStore, MonitorHTTPServer, lan_urls


def test_frame_store_returns_new_frames():
    store = FrameStore()
    assert store.latest() == (b"", 0)

    store.update(b"jpeg-data")

    assert store.latest() == (b"jpeg-data", 1)
    assert store.wait_for_next(0, timeout=0.01) == (b"jpeg-data", 1)


def test_monitor_http_read_only_endpoints():
    store = FrameStore()
    store.update(b"\xff\xd8fake-jpeg\xff\xd9")
    server = MonitorHTTPServer(("127.0.0.1", 0), store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with urllib.request.urlopen(base_url + "/", timeout=2) as response:
            assert response.status == 200
            body = response.read()
            assert b"/stream.mjpg" in body
            assert b"Seleccionar Directorio" in body
            assert b"Descargar" in body
            assert b">Salir<" not in body
            assert b"disabled title=\"Disponible solo en Qt\"" in body

        with urllib.request.urlopen(base_url + "/snapshot.jpg", timeout=2) as response:
            assert response.headers["Content-Type"] == "image/jpeg"
            assert response.read() == b"\xff\xd8fake-jpeg\xff\xd9"

        with urllib.request.urlopen(base_url + "/health", timeout=2) as response:
            assert response.read() == b'{"status":"ok","frame":1}'

        request = urllib.request.Request(base_url + "/", method="POST")
        try:
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 501
        else:
            raise AssertionError("El servidor no debe aceptar POST")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_can_browse_and_serve_result_images(tmp_path):
    results = tmp_path / "results"
    trigger = results / "2026-06-24" / "Trigger_0001_20260624_120000"
    trigger.mkdir(parents=True)
    image = trigger / "resultado_analisis.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    frame = trigger / "img_002.bmp"
    frame.write_bytes(b"fake-bmp")
    (trigger / "metricas.json").write_text(
        '{"exit_angle_deg": 45.0, "angle_frame": 2}',
        encoding="utf-8",
    )

    store = FrameStore()
    server = MonitorHTTPServer(("127.0.0.1", 0), store, results_root=results)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with urllib.request.urlopen(base_url + "/api/roots", timeout=2) as response:
            assert response.status == 200
            assert str(results).encode() in response.read()

        query = urllib.parse.urlencode({"path": str(trigger)})
        with urllib.request.urlopen(base_url + "/api/list?" + query, timeout=2) as response:
            body = response.read()
            assert b"resultado_analisis.png" in body
            assert b'"type": "image"' in body

        query = urllib.parse.urlencode({"path": str(image)})
        with urllib.request.urlopen(base_url + "/file?" + query, timeout=2) as response:
            assert response.headers["Content-Type"] == "image/png"
            assert response.read() == b"\x89PNG\r\n\x1a\nfake"

        with urllib.request.urlopen(base_url + "/api/results", timeout=2) as response:
            body = response.read()
            assert b"resultado_analisis.png" in body
            assert b'"items"' in body
            assert str(frame).encode() in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_converts_bmp_images_for_browser_display(tmp_path):
    results = tmp_path / "results"
    trigger = results / "2026-06-24" / "Trigger_0001_20260624_120000"
    trigger.mkdir(parents=True)
    image = trigger / "img_001.bmp"
    Image.new("L", (2, 2), color=128).save(image)

    store = FrameStore()
    server = MonitorHTTPServer(("127.0.0.1", 0), store, results_root=results)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        query = urllib.parse.urlencode({"path": str(image)})
        with urllib.request.urlopen(base_url + "/file?" + query, timeout=2) as response:
            body = response.read()
            assert response.headers["Content-Type"] == "image/png"
            assert body.startswith(b"\x89PNG\r\n\x1a\n")
            converted = Image.open(__import__("io").BytesIO(body))
            assert max(ImageStat.Stat(converted).mean) >= 120
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_analysis_control_endpoints():
    toggles = []
    running = False

    def toggle():
        nonlocal running
        running = not running
        toggles.append(running)

    store = FrameStore()
    server = MonitorHTTPServer(
        ("127.0.0.1", 0),
        store,
        analysis_toggle=toggle,
        analysis_state=lambda: running,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        with urllib.request.urlopen(base_url + "/api/analysis-state", timeout=2) as response:
            assert response.read() == b'{"running": false, "busy": false}'

        request = urllib.request.Request(
            base_url + "/api/action?action=toggle_analysis",
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.read() == b'{"accepted": true}'

        with urllib.request.urlopen(base_url + "/api/analysis-state", timeout=2) as response:
            assert response.read() == b'{"running": true, "busy": true}'
        assert toggles == [True]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_blocks_qt_only_actions():
    store = FrameStore()
    server = MonitorHTTPServer(("127.0.0.1", 0), store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        for action in ("select_directory", "download"):
            request = urllib.request.Request(
                base_url + f"/api/action?action={action}",
                method="POST",
            )
            try:
                urllib.request.urlopen(request, timeout=2)
            except urllib.error.HTTPError as exc:
                assert exc.code == 403
            else:
                raise AssertionError(f"La accion {action} no debe ejecutarse en web")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_dispatches_allowed_actions():
    actions = []
    store = FrameStore()
    server = MonitorHTTPServer(
        ("127.0.0.1", 0),
        store,
        action_callback=actions.append,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        request = urllib.request.Request(
            base_url + "/api/action?action=view_results",
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.read() == b'{"accepted": true, "action": "view_results"}'
        assert actions == ["view_results"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_analyze_saved_requires_selected_sequence_folder(tmp_path):
    results = tmp_path / "results"
    sequence = results / "Trigger_0001"
    sequence.mkdir(parents=True)
    (sequence / "img_001.bmp").write_bytes(b"fake")
    (sequence / "img_002.bmp").write_bytes(b"fake")
    requests = []

    store = FrameStore()
    server = MonitorHTTPServer(
        ("127.0.0.1", 0),
        store,
        results_root=results,
        saved_analysis_callback=requests.append,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        request = urllib.request.Request(
            base_url + "/api/action?action=analyze_saved",
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("Analizar rafaga web debe requerir carpeta seleccionada")

        request = urllib.request.Request(
            base_url + "/api/analyze-saved?" + urllib.parse.urlencode({"path": str(sequence)}),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert b'"accepted": true' in response.read()
        assert requests == [str(sequence)]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_rejects_exit_action():
    store = FrameStore()
    server = MonitorHTTPServer(("127.0.0.1", 0), store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        request = urllib.request.Request(
            base_url + "/api/action?action=exit",
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("El web no debe poder cerrar la aplicacion")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_monitor_web_blocks_file_browsing_while_busy(tmp_path):
    results = tmp_path / "results"
    trigger = results / "Trigger_0001"
    trigger.mkdir(parents=True)
    image = trigger / "resultado_analisis.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    store = FrameStore()
    server = MonitorHTTPServer(
        ("127.0.0.1", 0),
        store,
        results_root=results,
        busy_state=lambda: True,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"

    try:
        paths = [
            "/api/roots",
            "/api/results",
            "/api/list?" + urllib.parse.urlencode({"path": str(trigger)}),
            "/file?" + urllib.parse.urlencode({"path": str(image)}),
        ]
        for path in paths:
            try:
                urllib.request.urlopen(base_url + path, timeout=2)
            except urllib.error.HTTPError as exc:
                assert exc.code == 409
            else:
                raise AssertionError(f"{path} debe bloquearse durante analisis")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_lan_urls_include_port(monkeypatch):
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("192.168.1.20", 0))],
    )

    assert "http://192.168.1.20:8080" in lan_urls(8080)
