"""Genera la evidencia del historial de commits (git log) como imagen."""
import html
import os
import re
import subprocess
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE)
GIT = r"C:\Users\rootg\AppData\Local\aza-cloud\git\cmd\git.exe"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
OUT = os.path.join(BASE, "evidencias", "27_git_commits.png")


def git(*args) -> str:
    r = subprocess.run([GIT, "-C", RAIZ, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def commits() -> list[dict]:
    crudo = git("log", "--pretty=format:%h\x1f%ad\x1f%an\x1f%s", "--date=format:%Y-%m-%d %H:%M",
                "--shortstat", "--reverse")
    salida, actual = [], None
    for linea in crudo.splitlines():
        if "\x1f" in linea:
            h, fecha, autor, msj = linea.split("\x1f")
            actual = {"hash": h, "fecha": fecha, "autor": autor, "mensaje": msj,
                      "archivos": 0, "lineas": ""}
            salida.append(actual)
        elif "changed" in linea and actual:
            m = re.search(r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?", linea)
            if m:
                actual["archivos"] = int(m.group(1))
                partes = []
                if m.group(2):
                    partes.append(f"+{m.group(2)}")
                if m.group(3):
                    partes.append(f"−{m.group(3)}")
                actual["lineas"] = " ".join(partes)
    return salida


ESTILO = """
 body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef1f2;margin:0;padding:30px;color:#1c2427}
 h1{font-size:21px;margin:0 0 4px}
 .sub{color:#607d8b;font-size:13px;margin-bottom:20px}
 .card{background:#f7f9f9;border:1px solid #d6ddde;border-radius:10px;padding:6px 0;margin-bottom:16px}
 pre{background:#0f1a12;color:#c8e6c9;padding:16px 18px;border-radius:10px;margin:0;
     font-family:'Cascadia Mono',Consolas,monospace;font-size:12.5px;line-height:1.6}
 .fila{display:flex;gap:14px;align-items:flex-start;padding:9px 20px;border-bottom:1px solid #e3e8ea}
 .fila:last-child{border-bottom:0}
 .hash{font-family:Consolas,monospace;color:#154a1c;font-weight:700;font-size:12.5px;min-width:66px}
 .msj{flex:1;font-size:13.5px}
 .meta{font-size:11px;color:#78909c;font-family:Consolas,monospace;margin-top:3px}
 .num{font-size:11px;color:#4f6b57;font-family:Consolas,monospace;min-width:110px;text-align:right}
 .autor{background:#e3efe5;color:#154a1c;border-radius:20px;padding:1px 9px;font-size:11px}
"""


def main():
    lista = commits()
    filas = "".join(
        f"<div class='fila'><div class='hash'>{c['hash']}</div>"
        f"<div class='msj'>{html.escape(c['mensaje'])}"
        f"<div class='meta'>{c['fecha']} · <span class='autor'>{html.escape(c['autor'])}</span></div></div>"
        f"<div class='num'>{c['archivos']} archivo(s)<br>{c['lineas']}</div></div>"
        for c in reversed(lista))
    grafico = git("log", "--graph", "--oneline", "--decorate")
    total_a = sum(c["archivos"] for c in lista)
    pagina = f"""<!doctype html><html><head><meta charset='utf-8'><style>{ESTILO}</style></head><body>
    <h1>Historial de cambios del proyecto — Git</h1>
    <div class='sub'>{len(lista)} commits · rama <b>main</b> · {total_a} archivos versionados ·
    repositorio local del equipo (Leonardo Daza, José Sarabia, Daniel Paredes)</div>
    <div class='card'>{filas}</div>
    <div class='sub'>Salida de <code>git log --graph --oneline --decorate</code></div>
    <pre>{html.escape(grafico.strip())}</pre>
    </body></html>"""
    ruta = os.path.join(tempfile.gettempdir(), "evidencia_git.html")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(pagina)
    perfil = tempfile.mkdtemp(prefix="aza_git_")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=1440,1250", "--virtual-time-budget=3000",
                    f"--user-data-dir={perfil}", f"--screenshot={OUT}",
                    "file:///" + ruta.replace("\\", "/").replace(" ", "%20")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    print("   ok  27_git_commits.png")


if __name__ == "__main__":
    main()
