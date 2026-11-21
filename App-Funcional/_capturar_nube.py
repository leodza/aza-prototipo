"""Evidencias del sistema desplegado en AWS (app + pgweb de la base)."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

APP = "http://13.223.49.56:8000"
PGB = "http://13.223.49.56:8081"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
os.makedirs(OUT, exist_ok=True)


class Navegador:
    def __init__(self, url, puerto):
        self.perfil = tempfile.mkdtemp(prefix="aza_cloud_")
        self.proc = subprocess.Popen([
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--window-size=1440,1000", f"--remote-debugging-port={puerto}",
            f"--user-data-dir={self.perfil}", url,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pagina = None
        for _ in range(60):
            time.sleep(0.4)
            try:
                datos = json.load(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json"))
                p = [t for t in datos if t.get("type") == "page" and t.get("url", "").startswith("http")]
                if p:
                    pagina = p[0]
                    break
            except Exception:
                continue
        if not pagina:
            raise SystemExit("no se pudo abrir el navegador")
        self.ws = connect(pagina["webSocketDebuggerUrl"], max_size=60 * 1024 * 1024)
        self.n = 0
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")

    def cmd(self, metodo, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                return m.get("result", {})

    def js(self, exp):
        r = self.cmd("Runtime.evaluate", {"expression": exp, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value")

    def captura(self, nombre):
        r = self.cmd("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["data"]))
        print("   ok  ", nombre)

    def esperar(self, expr, segundos=60):
        for _ in range(int(segundos * 2)):
            if self.js(expr):
                return True
            time.sleep(0.5)
        return False

    def cerrar(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()


nav = Navegador(APP, 9666)
try:
    time.sleep(3)
    nav.captura("20_nube_login.png")

    nav.js("""(() => {
        const u = document.getElementById('login-usuario');
        u.value = 'jsarabia';
        u.dispatchEvent(new Event('change', {bubbles:true}));
        document.getElementById('login-pin').value = '1234';
        document.querySelector('.login-card').requestSubmit
            ? document.querySelector('.login-card').requestSubmit()
            : entrar(new Event('submit'));
        return 'ok';
    })()""")
    nav.esperar("document.getElementById('v-dashboard').classList.contains('activa')", 40)
    time.sleep(3)
    nav.captura("21_nube_dashboard.png")

    nav.js("irA('historico')")
    time.sleep(3)
    nav.captura("22_nube_historico.png")

    nav.js("irA('simulador'); document.getElementById('sim-velocidad').value='16'; actualizarVelocidad(); simular()")
    nav.esperar("document.getElementById('sim-resultado').querySelector('dl') !== null", 120)
    time.sleep(2)
    nav.captura("23_nube_simulador.png")
finally:
    nav.cerrar()

print("--- pgweb (base de datos en la nube) ---")
nav2 = Navegador(PGB, 9667)
try:
    time.sleep(14)
    nav2.captura("24_nube_pgweb.png")
finally:
    nav2.cerrar()
