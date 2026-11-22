"""Captura el dashboard local tras la prueba de estrés (secuencia probada)."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8000"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidencias")

perfil = tempfile.mkdtemp(prefix="aza_post2_")
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                         "--window-size=1440,1000", "--remote-debugging-port=9922",
                         f"--user-data-dir={perfil}", URL],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    pagina = None
    for _ in range(60):
        time.sleep(0.4)
        try:
            datos = json.load(urllib.request.urlopen("http://127.0.0.1:9922/json"))
            p = [t for t in datos if t.get("type") == "page"]
            if p:
                pagina = p[0]
                break
        except Exception:
            pass
    ws = connect(pagina["webSocketDebuggerUrl"], max_size=60 * 1024 * 1024)
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

    cmd("Page.enable")
    cmd("Runtime.enable")
    time.sleep(7)                                  # dejar cargar la SPA
    print("   hay formulario:", js("!!document.querySelector('.login-card')"))
    print("   usuarios:", js("JSON.stringify([...document.querySelectorAll('#login-usuario option')].map(o => o.value))"))

    js("""(() => {
        const u = document.getElementById('login-usuario');
        u.value = 'jsarabia';
        u.dispatchEvent(new Event('change', {bubbles:true}));
        document.getElementById('login-pin').value = '1234';
        document.querySelector('.login-card').requestSubmit();
        return 'ok';
    })()""")
    for _ in range(80):
        if js("document.getElementById('v-dashboard') && document.getElementById('v-dashboard').classList.contains('activa')"):
            print("   sesion iniciada")
            break
        time.sleep(0.5)
    time.sleep(4)
    r = cmd("Page.captureScreenshot", {"format": "png"})
    with open(os.path.join(OUT, "36_estres_app_despues.png"), "wb") as fh:
        fh.write(base64.b64decode(r["data"]))
    print("   ok   36_estres_app_despues.png")
    ws.close()
finally:
    proc.terminate()
