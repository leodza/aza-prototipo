"""Captura evidencias reales de la aplicación en ejecución mediante Chrome DevTools."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8000"
PUERTO = 9333
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
os.makedirs(OUT, exist_ok=True)

perfil = tempfile.mkdtemp(prefix="aza_chrome_")
proc = subprocess.Popen([
    CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--hide-scrollbars", "--window-size=1440,1000", f"--remote-debugging-port={PUERTO}",
    f"--user-data-dir={perfil}", URL,
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    pagina = None
    for _ in range(40):
        time.sleep(0.4)
        try:
            datos = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
            paginas = [t for t in datos if t.get("type") == "page" and t.get("url", "").startswith("http")]
            if paginas:
                pagina = paginas[0]
                break
        except Exception:
            continue
    if not pagina:
        print("No se pudo abrir la página")
        sys.exit(1)

    ws = connect(pagina["webSocketDebuggerUrl"], max_size=80 * 1024 * 1024)
    contador = [0]

    def cmd(metodo, params=None):
        contador[0] += 1
        ident = contador[0]
        ws.send(json.dumps({"id": ident, "method": metodo, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == ident:
                return msg

    def js(expresion):
        r = cmd("Runtime.evaluate", {"expression": expresion, "awaitPromise": True,
                                     "returnByValue": True, "userGesture": True})
        res = r.get("result", {})
        if "exceptionDetails" in res:
            print("   JS!", res["exceptionDetails"].get("text"),
                  res["exceptionDetails"].get("exception", {}).get("description", "")[:200])
        return res.get("result", {}).get("value")

    def esperar(condicion, limite=25):
        for _ in range(limite * 4):
            if js(condicion):
                return True
            time.sleep(0.25)
        return False

    def captura(nombre):
        r = cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["result"]["data"]))
        print("   ok  ", nombre)

    cmd("Page.enable")
    cmd("Runtime.enable")

    if not esperar("typeof entrar === 'function'", 30):
        print("La aplicación no cargó")
        sys.exit(1)
    time.sleep(1.2)
    captura("01_login.png")

    print("· iniciando sesión como supervisor")
    js("document.getElementById('login-usuario').value='jsarabia';"
       "document.getElementById('login-pin').value='1234';"
       "entrar(new Event('submit'))")
    esperar("document.getElementById('app').style.display === 'flex'", 25)
    esperar("document.getElementById('kpi-total').textContent !== '—'", 25)
    time.sleep(1.0)
    captura("02_dashboard.png")

    print("· simulando una ráfaga de cámara")
    js("irA('simulador')")
    time.sleep(0.4)
    js("simular()")
    esperar("document.getElementById('sim-resultado').querySelector('dl') !== null", 60)
    time.sleep(1.2)
    captura("03_simulador.png")

    print("· simulación con velocidad alta y rechazo forzado")
    js("document.getElementById('sim-velocidad').value='28'; actualizarVelocidad();"
       "document.getElementById('sim-modo').value='fuera'; simular()")
    time.sleep(11)
    captura("03b_simulador_velocidad.png")
    js("document.getElementById('sim-velocidad').value='12'; actualizarVelocidad();"
       "document.getElementById('sim-modo').value='dentro';")

    print("· abriendo el detalle de la inspección simulada")
    js("verDetalle(window.__ultimaSim)")
    time.sleep(1.8)
    captura("04_detalle.png")

    print("· histórico con filtros y orden lote → batch")
    js("irA('historico')")
    time.sleep(1.8)
    captura("05_historico.png")

    print("· recetas y auditoría")
    js("irA('recetas')")
    time.sleep(1.2)
    captura("06_recetas.png")
    js("window.scrollTo(0, 640)")
    time.sleep(0.9)
    captura("06b_materiales.png")
    js("window.scrollTo(0, 0)")
    js("irA('auditoria')")
    time.sleep(1.2)
    captura("07_auditoria.png")

    print("· usuarios (requiere admin): cerrando y entrando como administrador")
    js("salir()")
    time.sleep(1.2)
    js("document.getElementById('login-usuario').value='dparedes';"
       "document.getElementById('login-pin').value='1234';"
       "entrar(new Event('submit'))")
    esperar("document.getElementById('app').style.display === 'flex'", 25)
    time.sleep(1.2)
    js("irA('usuarios')")
    time.sleep(1.4)
    captura("08_usuarios.png")

    print("· prueba de RBAC: recetas como administrador")
    js("irA('recetas')")
    time.sleep(1.0)
    captura("09_recetas_admin.png")

    print("· menú restringido para el rol operador")
    js("salir()")
    time.sleep(1.2)
    js("document.getElementById('login-usuario').value='ldaza';"
       "document.getElementById('login-pin').value='1234';"
       "entrar(new Event('submit'))")
    esperar("document.getElementById('app').style.display === 'flex'", 25)
    time.sleep(1.4)
    captura("10_operador.png")

    print("· desplazamiento en el simulador (barra lateral fija)")
    js("irA('simulador')")
    time.sleep(0.6)
    js("simular()")
    esperar("document.getElementById('sim-resultado').querySelector('dl') !== null", 60)
    js("window.scrollTo(0, 620)")
    time.sleep(1.0)
    captura("11_simulador_scroll.png")

    ws.close()
    print("\nCapturas en:", OUT)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
