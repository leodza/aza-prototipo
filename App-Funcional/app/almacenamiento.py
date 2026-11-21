"""Almacenamiento de imágenes de ráfaga: sistema local o MinIO / S3.

En desarrollo se escribe en `data/capturas`. En la nube se sube a MinIO
(compatible con S3) y la base de datos solo guarda la clave del objeto.

Se configura con variables de entorno:
    AZA_ALMACEN        local | s3          (por defecto local)
    AZA_S3_ENDPOINT    http://minio:9000   (en AWS: http://127.0.0.1:9000 o el endpoint de S3)
    AZA_S3_ACCESS      usuario
    AZA_S3_SECRET      contraseña
    AZA_S3_BUCKET      aza-capturas
    AZA_S3_REGION      us-east-1
    AZA_S3_PUBLICO     1 para permitir lectura anónima (solo demostración)
"""
from __future__ import annotations

import io
import os

MODO = os.getenv("AZA_ALMACEN", "local").strip().lower()
ENDPOINT = os.getenv("AZA_S3_ENDPOINT", "http://127.0.0.1:9000")
ACCESS = os.getenv("AZA_S3_ACCESS", "minioadmin")
SECRET = os.getenv("AZA_S3_SECRET", "minioadmin")
BUCKET = os.getenv("AZA_S3_BUCKET", "aza-capturas")
REGION = os.getenv("AZA_S3_REGION", "us-east-1")
PUBLICO = os.getenv("AZA_S3_PUBLICO", "0") == "1"

_cliente = None
_bucket_listo = False


def _verificar_bucket() -> None:
    """Crea el bucket la primera vez que se necesita (idempotente)."""
    global _bucket_listo
    if _bucket_listo or not activo():
        return
    try:
        _s3().head_bucket(Bucket=BUCKET)
    except Exception:
        try:
            _s3().create_bucket(Bucket=BUCKET)
        except Exception:
            pass
    _bucket_listo = True


def activo() -> bool:
    return MODO == "s3"


def descripcion() -> str:
    if activo():
        return f"MinIO/S3 · bucket «{BUCKET}» en {ENDPOINT}"
    return "sistema de archivos local (data/capturas)"


def _s3():
    global _cliente
    if _cliente is None:
        import boto3
        from botocore.config import Config
        # Si no hay endpoint se usa el S3 real de AWS (con el rol de la instancia);
        # si hay endpoint se apunta a MinIO / SeaweedFS / cualquier S3 compatible.
        extra = {}
        if ENDPOINT:
            extra["endpoint_url"] = ENDPOINT
        _cliente = boto3.client(
            "s3",
            region_name=REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if ENDPOINT else "virtual"},
                retries={"max_attempts": 2, "mode": "standard"},
            ),
            **extra,
        )
    return _cliente


def asegurar_bucket() -> dict:
    """Crea el bucket si no existe. Devuelve un resumen del estado."""
    if not activo():
        return {"modo": "local", "bucket": None, "objetos": 0}
    s3 = _s3()
    try:
        s3.head_bucket(Bucket=BUCKET)
        creado = False
    except Exception:
        s3.create_bucket(Bucket=BUCKET)
        creado = True
    if PUBLICO:
        politica = ('{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
                    '"Principal":{"AWS":["*"]},"Action":["s3:GetObject"],'
                    f'"Resource":["arn:aws:s3:::{BUCKET}/*"]}}]}}')
        try:
            s3.put_bucket_policy(Bucket=BUCKET, Policy=politica)
        except Exception:
            pass
    return {"modo": "s3", "bucket": BUCKET, "creado": creado,
            "objetos": contar_objetos()}


def contar_objetos() -> int:
    if not activo():
        return 0
    _verificar_bucket()
    try:
        paginador = _s3().get_paginator("list_objects_v2")
        total = 0
        for pagina in paginador.paginate(Bucket=BUCKET):
            total += pagina.get("KeyCount", 0)
        return total
    except Exception:
        return 0


def subir_archivo(ruta_local: str, clave: str, tipo: str = "image/png") -> str:
    """Sube un archivo y devuelve la clave del objeto."""
    if not activo():
        return ""
    _verificar_bucket()
    _s3().upload_file(ruta_local, BUCKET, clave, ExtraArgs={"ContentType": tipo})
    return clave


def subir_carpeta(rutas: list[tuple[str, str]]) -> list[str]:
    """Sube varios archivos: lista de (ruta_local, clave)."""
    subidos = []
    for ruta, clave in rutas:
        tipo = "image/bmp" if clave.lower().endswith(".bmp") else "image/png"
        if clave.lower().endswith(".json"):
            tipo = "application/json"
        subidos.append(subir_archivo(ruta, clave, tipo))
    return subidos


def leer(clave: str) -> bytes | None:
    if not activo() or not clave:
        return None
    try:
        buf = io.BytesIO()
        _s3().download_fileobj(BUCKET, clave, buf)
        return buf.getvalue()
    except Exception:
        return None


def url(clave: str) -> str | None:
    """URL directa del objeto (solo si el bucket es público o para la consola)."""
    if not activo() or not clave:
        return None
    base = ENDPOINT.rstrip("/")
    return f"{base}/{BUCKET}/{clave}"
