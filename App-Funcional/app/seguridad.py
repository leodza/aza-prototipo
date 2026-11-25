"""Autenticación, tokens y control de acceso (RBAC).

Implementa el diseño del informe ES2 sin dependencias externas:
  · PIN almacenado con PBKDF2-HMAC-SHA256 (200 000 iteraciones y sal única).
  · Token de acceso tipo JWT HS256, con vigencia de 15 minutos.
  · Token de refresco opaco, guardado como hash, con rotación y revocación.
  · Bloqueo de la cuenta tras cinco intentos fallidos.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

ITERACIONES = 200_000
SAL_LEN = 16
SECRETO = os.getenv("AZA_SECRETO", "prototipo-aza-clave-de-demostracion-2026")
VIDA_ACCESO_SEG = 15 * 60          # 15 minutos
VIDA_REFRESCO_H = 8                # 8 horas
MAX_INTENTOS = 5
BLOQUEO_MIN = 15


# --------------------------------------------------------------------------- #
# PIN
# --------------------------------------------------------------------------- #
def hash_pin(pin: str) -> str:
    sal = os.urandom(SAL_LEN)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), sal, ITERACIONES)
    return f"pbkdf2${ITERACIONES}${base64.b64encode(sal).decode()}${base64.b64encode(dk).decode()}"


def verificar_pin(pin: str, almacenado: str) -> bool:
    try:
        _, iteraciones, sal_b64, dk_b64 = almacenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), base64.b64decode(sal_b64),
                                 int(iteraciones))
        return hmac.compare_digest(base64.b64encode(dk).decode(), dk_b64)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# JWT HS256 mínimo
# --------------------------------------------------------------------------- #
def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _b64d(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def crear_jwt(payload: dict, vida_seg: int = VIDA_ACCESO_SEG) -> str:
    cabecera = {"alg": "HS256", "typ": "JWT"}
    cuerpo = dict(payload)
    cuerpo["exp"] = int(time.time()) + vida_seg
    cuerpo["iat"] = int(time.time())
    partes = [_b64(json.dumps(cabecera, separators=(",", ":")).encode()),
              _b64(json.dumps(cuerpo, separators=(",", ":")).encode())]
    firma = hmac.new(SECRETO.encode(), ".".join(partes).encode(), hashlib.sha256).digest()
    partes.append(_b64(firma))
    return ".".join(partes)


def leer_jwt(token: str) -> dict | None:
    """Devuelve el payload si la firma es válida y no expiró; si no, None."""
    try:
        cab, cuerpo, firma = token.split(".")
        esperado = hmac.new(SECRETO.encode(), f"{cab}.{cuerpo}".encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(esperado), firma):
            return None
        datos = json.loads(_b64d(cuerpo))
        if datos.get("exp", 0) < int(time.time()):
            return None
        return datos
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Token de refresco
# --------------------------------------------------------------------------- #
def nuevo_refresh() -> tuple[str, str, datetime]:
    """Devuelve (token_en_claro, hash_para_guardar, expiración)."""
    claro = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=VIDA_REFRESCO_H)
    return claro, hash_refresh(claro), expira


def hash_refresh(claro: str) -> str:
    return hashlib.sha256(claro.encode()).hexdigest()


def iguales(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

def validar_clave(clave: str) -> list[str]:
    """Devuelve los requisitos que faltan para una contrasena segura.

    Se exige un minimo de ocho caracteres con mayuscula, minuscula y numero.
    Devuelve una lista vacia cuando la clave cumple.
    """
    faltan = []
    if len(clave or '') < 8:
        faltan.append('al menos 8 caracteres')
    if not any(c.islower() for c in clave or ''):
        faltan.append('una minuscula')
    if not any(c.isupper() for c in clave or ''):
        faltan.append('una mayuscula')
    if not any(c.isdigit() for c in clave or ''):
        faltan.append('un numero')
    return faltan
