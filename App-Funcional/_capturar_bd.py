"""Captura evidencias de PostgreSQL (pgweb) mediante Chrome DevTools."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8081"
PUERTO = 9444
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
os.makedirs(OUT, exist_ok=True)

perfil = tempfile.mkdtemp(prefix="aza_pgweb_")
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
        raise SystemExit("no se pudo abrir pgweb")

    ws = connect(pagina["webSocketDebuggerUrl"], max_size=60 * 1024 * 1024)
    contador = [0]

    def cmd(metodo, params=None):
        contador[0] += 1
        ident = contador[0]
        ws.send(json.dumps({"id": ident, "method": metodo, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == ident:
                return msg

    def js(exp):
        r = cmd("Runtime.evaluate", {"expression": exp, "awaitPromise": True, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def captura(nombre):
        r = cmd("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["result"]["data"]))
        print("   ok  ", nombre)

    cmd("Page.enable")
    cmd("Runtime.enable")
    time.sleep(4)
    captura("12_bd_tablas.png")

    def abrir_tabla(nombre):
        return js(f"""(() => {{
            const cand = [...document.querySelectorAll('div, span, i')]
                .filter(e => (e.textContent || '').toLowerCase().includes('{nombre}'))
                .sort((a, b) => a.textContent.length - b.textContent.length);
            if (!cand.length) return 'no encontrado';
            const el = cand[0];
            el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            return 'click:' + el.tagName + ':' + el.textContent.trim().slice(0, 20);
        }})()""")

    for tabla, archivo in [("inspecciones", "13_bd_inspecciones.png"),
                           ("materiales", "14_bd_materiales.png"),
                           ("usuarios", "15_bd_usuarios.png"),
                           ("lotes", "16_bd_lotes.png"),
                           ("auditoria", "17_bd_auditoria.png")]:
        r = abrir_tabla(tabla)
        time.sleep(3.5)
        captura(archivo)
        print("     ", tabla, "->", r)

    ws.close()
    print("listo")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
