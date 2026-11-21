# database/auth.py — Autenticación y CRUD de usuarios
import sqlite3
import hashlib
import os
import base64
from src.core.config import DB_PATH

_PBKDF2_ITERATIONS = 100_000
_SALT_LEN = 16


def _hash_pin(pin: str, salt: bytes | None = None) -> str:
    """PBKDF2-HMAC-SHA256 con salt aleatorio. Retorna 'salt$hash' en base64."""
    if salt is None:
        salt = os.urandom(_SALT_LEN)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def _verify_pin(pin: str, stored: str) -> bool:
    """Verifica un PIN contra un hash almacenado 'salt$hash'."""
    try:
        salt_b64, dk_b64 = stored.split("$", 1)
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return base64.b64encode(dk).decode() == dk_b64
    except (ValueError, Exception):
        return False


def crear_usuario(username: str, pin: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios(username, pin_hash, activo) VALUES(?, ?, 1)",
        (username.strip(), _hash_pin(pin))
    )
    conn.commit()
    conn.close()


def validar_login(username: str, pin: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT pin_hash, activo FROM usuarios WHERE username=?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    pin_hash, activo = row
    if int(activo) != 1:
        return False
    if "$" in pin_hash:
        return _verify_pin(pin, pin_hash)
    return pin_hash == hashlib.sha256(pin.encode("utf-8")).hexdigest()


def borrar_usuario(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id=?", (int(user_id),))
    conn.commit()
    conn.close()


def listar_usuarios_activos():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username FROM usuarios WHERE activo=1 ORDER BY username")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def es_admin(username: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM usuarios WHERE username=?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    return bool(row and int(row[0]) == 1)


def listar_usuarios():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, username, activo, is_admin FROM usuarios ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return rows


def set_usuario_activo(user_id: int, activo: bool):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if activo else 0, int(user_id)))
    conn.commit()
    conn.close()


def reset_pin(user_id: int, new_pin: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET pin_hash=? WHERE id=?", (_hash_pin(new_pin), int(user_id)))
    conn.commit()
    conn.close()
