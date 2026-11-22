# -*- coding: utf-8 -*-
"""Evidencia: captura de la consola real de la prueba ejecutada contra la nube."""
import html
import json
import os
import subprocess
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.join(os.path.dirname(BASE), "evidencias")
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
NUBE = json.load(open(os.path.join(BASE, "resultados_nube.json"), encoding="utf-8"))
log_nube = open(os.path.join(BASE, "consola_nube.log"), encoding="utf-8").read()

ESTILO = """
 body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef1f2;margin:0;padding:26px;color:#1c2427}
 h1{font-size:19px;margin:0 0 4px;color:#154a1c}
 .sub{color:#607d8b;font-size:12.5px;margin-bottom:16px}
 pre{background:#0f1a12;color:#c8e6c9;padding:16px 18px;border-radius:10px;font-size:11.5px;
     line-height:1.5;font-family:'Cascadia Mono',Consolas,monospace;white-space:pre-wrap;margin:0}
"""

pagina = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    f"<style>{ESTILO}</style></head><body>"
    "<h1>Prueba de estrés ejecutada contra la nube</h1>"
    f"<div class='sub'>{html.escape(NUBE['base'])} · {html.escape(NUBE['backend'])} · "
    f"{html.escape(NUBE['inicio'])}</div>"
    f"<pre>{html.escape(log_nube)}</pre></body></html>"
)

ruta = os.path.join(tempfile.gettempdir(), "ev_consola_nube.html")
with open(ruta, "w", encoding="utf-8") as fh:
    fh.write(pagina)

perfil = tempfile.mkdtemp(prefix="aza_cn_")
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--window-size=1440,1150", "--virtual-time-budget=3000",
                f"--user-data-dir={perfil}",
                f"--screenshot={os.path.join(EVID, '40_estres_consola_nube.png')}",
                "file:///" + ruta.replace("\\", "/")],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
print("   ok   40_estres_consola_nube.png")
