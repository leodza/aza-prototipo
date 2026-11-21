"""Captura pgweb (base de datos en vivo) con autenticación básica."""
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL = "http://13.223.49.56:8081"
AUTH = "Basic " + base64.b64encode(b"aza:AzaLab2026Db").decode()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")

perfil = tempfile.mkdtemp(prefix="aza_pgw_")
proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                         "--window-size=1440,1000", "--remote-debugging-port=9888",
                         f"--user-data-dir={perfil}", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    pagina = None
    for _ in range(50):
        time.sleep(0.4)
        try:
            datos = json.load(urllib.request.urlopen("http://127.0.0.1:9888/json"))
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

    def captura(nombre):
        r = cmd("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(OUT, nombre), "wb") as fh:
            fh.write(base64.b64decode(r["data"]))
        print("   ok  ", nombre)

    cmd("Page.enable")
    cmd("Runtime.enable")
    cmd("Network.enable")
    cmd("Network.setExtraHTTPHeaders", {"headers": {"Authorization": AUTH}})
    cmd("Page.navigate", {"url": URL})
    time.sleep(9)
    captura("24_nube_pgweb.png")

    # escribir una consulta real en el editor Ace y ejecutarla
    r = js(r"""(() => {
        const el = document.querySelector('.ace_editor');
        if (!el || typeof ace === 'undefined') return 'sin editor ace';
        const ed = ace.edit(el);
        ed.setValue('SELECT i.id, i.fecha_hora::date AS fecha, i.lote_id, i.batch_id, i.receta_id, ' +
                    'left(i.material,20) AS material, i.angulo, i.estado, ' +
                    'left(coalesce(i.imagen_clave,\'sin objeto\'),34) AS objeto ' +
                    'FROM inspecciones i ORDER BY i.id DESC LIMIT 8;', 1);
        return 'consulta escrita';
    })()""")
    print('      editor:', r)
    time.sleep(1)
    r2 = js(r"""(() => {
        const b = [...document.querySelectorAll('button,a,div,span')]
            .filter(e => (e.textContent || '').trim() === 'Run Query');
        if (!b.length) return 'sin boton';
        b[0].click(); return 'run';
    })()""")
    print('      ejecutar:', r2)
    time.sleep(4)
    captura("28_nube_pgweb_inspecciones.png")
    ws.close()
finally:
    proc.terminate()
