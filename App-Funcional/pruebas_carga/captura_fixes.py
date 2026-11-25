"""Captura recetas y usuarios después de los arreglos."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidencias")
perfil = tempfile.mkdtemp(prefix="aza_fix_")
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                         "--window-size=1600,950", "--remote-debugging-port=9944",
                         "--user-data-dir=" + perfil, "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    pagina = None
    for _ in range(60):
        time.sleep(0.4)
        try:
            datos = json.load(urllib.request.urlopen("http://127.0.0.1:9944/json"))
            p = [t for t in datos if t.get("type") == "page"]
            if p:
                pagina = p[0]
                break
        except Exception:
            pass
    ws = connect(pagina["webSocketDebuggerUrl"], max_size=80 * 1024 * 1024)
    n = [0]

    def cmd(metodo, params=None):
        n[0] += 1
        ws.send(json.dumps({"id": n[0], "method": metodo, "params": params or {}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == n[0]:
                return m.get("result", {})

    def js(exp):
        r = cmd("Runtime.evaluate", {"expression": exp, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value")

    def captura(nombre):
        r = cmd("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["data"]))
        print("   ok  ", nombre)

    cmd("Page.enable")
    cmd("Runtime.enable")
    cmd("Page.navigate", {"url": "http://127.0.0.1:8000/"})
    time.sleep(6)
    js("""(() => { document.getElementById('login-usuario').value='dparedes';
        document.getElementById('login-pin').value='1234';
        document.querySelector('.login-card').requestSubmit(); return 1; })()""")
    time.sleep(6)

    js("irA('recetas')")
    time.sleep(3)
    print("   texto recetas:", str(js("document.getElementById('v-recetas').innerText.slice(0,120)")))
    captura("58_recetas_ok.png")

    js("irA('usuarios')")
    time.sleep(3)
    captura("59_usuarios_aireado.png")

    js("irA('respaldos')")
    time.sleep(3)
    js("window.scrollTo(0, 400)")
    time.sleep(1)
    captura("60_importar_respaldo.png")
    ws.close()
finally:
    proc.terminate()
