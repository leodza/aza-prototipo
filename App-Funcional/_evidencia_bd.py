"""Genera las evidencias de la base de datos y del almacenamiento de objetos.

Ejecuta consultas reales contra PostgreSQL (psql) y contra el almacenamiento S3,
y arma páginas HTML que luego se capturan como imagen.
"""
import base64
import html
import json
import os
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "evidencias")
os.makedirs(OUT, exist_ok=True)
PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
URL_DB = os.getenv("AZA_PG_URL", "postgresql://postgres@127.0.0.1:5433/aza")


def sql(consulta: str) -> str:
    r = subprocess.run([PSQL, "-d", URL_DB, "-P", "pager=off", "-c", consulta],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


CONSULTAS = [
    ("Estructura de la base (tablas creadas por la aplicación)",
     r"\dt"),
    ("Usuarios y roles",
     "SELECT u.id, u.username, u.nombre, r.nombre AS rol, u.activo "
     "FROM usuarios u JOIN roles r ON r.id = u.rol_id ORDER BY u.id;"),
    ("Catálogo de materiales del trazado",
     "SELECT id, familia, tipo, descripcion, activo FROM materiales ORDER BY familia, tipo;"),
    ("Recetas asociadas a material",
     "SELECT r.id, r.nombre, r.min_tol, r.max_tol, r.espesor_mm, m.familia || ' ' || m.tipo AS material "
     "FROM recetas r LEFT JOIN materiales m ON m.id = r.material_id ORDER BY r.id;"),
    ("Lotes y batches (orden de trazado)",
     "SELECT l.id AS lote_id, l.codigo AS lote, l.turno, b.id AS batch_id, b.numero AS batch, "
     "l.receta_id FROM lotes l JOIN batches b ON b.lote_id = l.id ORDER BY l.codigo, b.numero;"),
    ("Inspecciones registradas (últimas 12)",
     "SELECT i.id, i.fecha_hora::date AS fecha, i.lote_id, i.batch_id, i.receta_id, "
     "left(i.material, 22) AS material, i.angulo, i.estado, i.velocidad_m_min AS vel, "
     "left(coalesce(i.imagen_clave, '-'), 26) AS objeto "
     "FROM inspecciones i ORDER BY i.id DESC LIMIT 12;"),
    ("Totales por tabla",
     "SELECT 'usuarios' AS tabla, count(*) FROM usuarios UNION ALL "
     "SELECT 'materiales', count(*) FROM materiales UNION ALL "
     "SELECT 'recetas', count(*) FROM recetas UNION ALL "
     "SELECT 'lotes', count(*) FROM lotes UNION ALL "
     "SELECT 'batches', count(*) FROM batches UNION ALL "
     "SELECT 'inspecciones', count(*) FROM inspecciones UNION ALL "
     "SELECT 'auditoria', count(*) FROM auditoria ORDER BY 1;"),
    ("Bitácora de auditoría (últimos 8 eventos)",
     "SELECT fecha, accion, entidad, entidad_id, left(coalesce(detalle, ''), 46) AS detalle "
     "FROM auditoria ORDER BY id DESC LIMIT 8;"),
]


def objetos_s3() -> list[dict]:
    import boto3
    from botocore.config import Config
    endpoint = os.getenv("AZA_S3_ENDPOINT") or None
    extra = {"endpoint_url": endpoint} if endpoint else {}
    s3 = boto3.client(
        "s3", region_name=os.getenv("AZA_S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4",
                      s3={"addressing_style": "path" if endpoint else "virtual"}),
        **extra)
    salida = []
    paginador = s3.get_paginator("list_objects_v2")
    for pagina in paginador.paginate(Bucket=os.getenv("AZA_S3_BUCKET", "aza-capturas")):
        for o in pagina.get("Contents", []):
            salida.append({"clave": o["Key"], "bytes": o["Size"],
                           "modificado": o["LastModified"].strftime("%Y-%m-%d %H:%M")})
    return salida


ESTILO = """
 body{font-family:'Segoe UI',system-ui,sans-serif;background:#eef1f2;margin:0;padding:28px;color:#1c2427}
 h1{font-size:20px;margin:0 0 4px}
 .sub{color:#607d8b;font-size:13px;margin-bottom:18px}
 .card{background:#f7f9f9;border:1px solid #d6ddde;border-radius:10px;padding:18px 20px;margin-bottom:16px;
       box-shadow:0 1px 2px rgba(16,24,40,.06)}
 h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#154a1c;margin:0 0 10px}
 pre{background:#0f1a12;color:#c8e6c9;padding:14px 16px;border-radius:8px;font-size:12px;line-height:1.45;
     overflow:hidden;margin:0;font-family:'Cascadia Mono',Consolas,monospace;white-space:pre-wrap}
 .meta{font-size:11px;color:#78909c;margin-top:8px;font-family:'Cascadia Mono',Consolas,monospace}
 table{width:100%;border-collapse:collapse;font-size:12.5px}
 th{text-align:left;background:#154a1c;color:#fff;padding:7px 9px;font-size:11px;text-transform:uppercase;
    letter-spacing:.05em}
 td{padding:6px 9px;border-bottom:1px solid #e3e8ea;font-family:Consolas,monospace}
 tr:nth-child(even) td{background:#eef3ef}
"""


def pagina_bd() -> str:
    partes = []
    for titulo, consulta in CONSULTAS:
        salida = sql(consulta)
        partes.append(
            f"<div class='card'><h2>{html.escape(titulo)}</h2>"
            f"<pre>{html.escape(salida.strip())}</pre>"
            f"<div class='meta'>psql &gt; {html.escape(consulta.strip()[:110])}</div></div>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{ESTILO}</style></head><body>"
            f"<h1>Base de datos PostgreSQL — esquema <code>aza</code></h1>"
            f"<div class='sub'>Salida real de <b>psql</b> contra el servidor PostgreSQL 18 · "
            f"base <code>aza</code> · {time.strftime('%Y-%m-%d %H:%M')}</div>"
            + "".join(partes) + "</body></html>")


def pagina_objetos() -> str:
    objetos = objetos_s3()
    total = sum(o["bytes"] for o in objetos)
    filas = "".join(
        f"<tr><td>{html.escape(o['clave'])}</td><td>{o['bytes']:,}</td><td>{o['modificado']}</td></tr>"
        for o in objetos[:40])
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{ESTILO}</style></head><body>"
            f"<h1>Almacenamiento de objetos — bucket "
            f"<code>{os.getenv('AZA_S3_BUCKET', 'aza-capturas')}</code></h1>"
            f"<div class='sub'>Listado real vía API S3 (compatible con MinIO) · "
            f"{len(objetos)} objetos · {total/1024/1024:.1f} MB · "
            f"{time.strftime('%Y-%m-%d %H:%M')}</div>"
            f"<div class='card'><h2>Objetos almacenados (primeros 40)</h2>"
            f"<table><thead><tr><th>Clave del objeto</th><th>Bytes</th><th>Modificado</th></tr></thead>"
            f"<tbody>{filas}</tbody></table></div></body></html>")


def capturar_html(archivo_html: str, destino: str, alto: int = 1150):
    perfil = tempfile.mkdtemp(prefix="aza_ev_")
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                             "--window-size=1440,{0}".format(alto), "--virtual-time-budget=3000",
                             f"--user-data-dir={perfil}", f"--screenshot={destino}",
                             "file:///" + archivo_html.replace("\\", "/").replace(" ", "%20")],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.wait(timeout=120)


if __name__ == "__main__":
    html_bd = os.path.join(tempfile.gettempdir(), "evidencia_bd.html")
    with open(html_bd, "w", encoding="utf-8") as fh:
        fh.write(pagina_bd())
    capturar_html(html_bd, os.path.join(OUT, os.getenv("AZA_EV_BD", "12_bd_postgresql.png")), 2700)
    print("   ok  12_bd_postgresql.png")

    html_obj = os.path.join(tempfile.gettempdir(), "evidencia_objetos.html")
    with open(html_obj, "w", encoding="utf-8") as fh:
        fh.write(pagina_objetos())
    capturar_html(html_obj, os.path.join(OUT, os.getenv("AZA_EV_OBJ", "13_objetos_s3.png")), 1400)
    print("   ok  13_objetos_s3.png")
