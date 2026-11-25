"""Captura la interfaz nueva con navegación explícita (robusta)."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8000/"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidencias")


class Navegador:
    def __init__(self, puerto):
        self.perfil = tempfile.mkdtemp(prefix="aza_ui_")
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1440,980", f"--remote-debugging-port={puerto}",
             f"--user-data-dir={self.perfil}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pagina = None
        for _ in range(60):
            time.sleep(0.4)
            try:
                datos = json.load(urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json"))
                p = [t for t in datos if t.get("type") == "page"]
                if p:
                    pagina = p[0]
                    break
            except Exception:
                pass
        self.ws = connect(pagina["webSocketDebuggerUrl"], max_size=80 * 1024 * 1024)
        self.n = 0
        self.cmd("Page.enable")
        self.cmd("Runtime.enable")
        self.cmd("Page.navigate", {"url": URL})
        self.esperar("!!document.querySelector('.login-card')", 25)

    def cmd(self, metodo, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                return m.get("result", {})

    def js(self, exp):
        for intento in range(3):
            r = self.cmd("Runtime.evaluate", {"expression": exp, "returnByValue": True,
                                              "awaitPromise": True})
            if r.get("exceptionDetails"):
                time.sleep(0.4)
                continue
            return r.get("result", {}).get("value")
        return None

    def esperar(self, expr, segundos=25):
        for _ in range(int(segundos * 2)):
            if self.js(expr):
                return True
            time.sleep(0.5)
        return False

    def captura(self, nombre):
        r = self.cmd("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["data"]))
        print("   ok  ", nombre)

    def cerrar(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()


nav = Navegador(9991)
try:
    print("   url:", nav.js("document.URL"))
    print("   formulario:", nav.js("!!document.querySelector('.login-card')"))
    time.sleep(2)
    nav.captura("41_login_nuevo.png")

    nav.js("""(() => {
        document.getElementById('login-usuario').value = 'dparedes';
        document.getElementById('login-pin').value = '1234';
        document.querySelector('.login-card').requestSubmit();
        return 'ok';
    })()""")
    print("   sesión iniciada:", nav.esperar("!!(window.estado && estado.access)", 25))
    time.sleep(3)
    nav.captura("42_dashboard_oscuro.png")

    for vista, archivo in [("recetas", "43_recetas_botones.png"),
                           ("alarmas", "45_alarmas.png"),
                           ("estadisticas", "48_estadisticas.png"),
                           ("respaldos", "49_respaldos.png"),
                           ("configuracion", "46_configuracion.png"),
                           ("historico", "47_historico_operador.png")]:
        nav.js(f"irA('{vista}')")
        time.sleep(2.5)
        nav.captura(archivo)

    nav.js("irA('estadisticas'); compararOperadores()")
    time.sleep(3)
    nav.js("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)
    nav.captura("50_comparador_pares.png")
    nav.js("window.scrollTo(0, 0)")

    nav.js("irA('usuarios'); abrirPermisos(1)")
    time.sleep(2.5)
    nav.captura("51_permisos_usuario.png")
    nav.js("cerrarModal('modal-permisos')")

    nav.js("irA('recetas'); abrirModal('modal-receta')")
    time.sleep(1.5)
    nav.captura("44_modal_receta.png")
    nav.js("cerrarModal('modal-receta')")
finally:
    nav.cerrar()
