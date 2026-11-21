from src.database.auth import _hash_pin, _verify_pin, crear_usuario, validar_login, es_admin
from src.database.models import inicializar_db


def test_hash_pin_produces_salt_and_hash():
    result = _hash_pin("1234")
    parts = result.split("$")
    assert len(parts) == 2
    assert len(parts[0]) > 0
    assert len(parts[1]) > 0


def test_hash_pin_different_each_time():
    h1 = _hash_pin("1234")
    h2 = _hash_pin("1234")
    assert h1 != h2


def test_verify_pin_correct():
    stored = _hash_pin("my_secret")
    assert _verify_pin("my_secret", stored) is True


def test_verify_pin_wrong():
    stored = _hash_pin("my_secret")
    assert _verify_pin("wrong", stored) is False


def test_verify_pin_invalid_format():
    assert _verify_pin("any", "no_dollar_sign") is False


def test_backward_compat_legacy_sha256(tmp_db):
    import sqlite3
    import hashlib
    inicializar_db()
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    legacy_hash = hashlib.sha256("1234".encode("utf-8")).hexdigest()
    cur.execute("INSERT INTO usuarios(username, pin_hash, activo, is_admin) VALUES (?, ?, 1, 0)",
                ("legacy_user", legacy_hash))
    conn.commit()
    conn.close()

    assert validar_login("legacy_user", "1234") is True
    assert validar_login("legacy_user", "wrong") is False


def test_crud_usuario(tmp_db):
    inicializar_db()
    crear_usuario("testop", "5678")
    assert validar_login("testop", "5678") is True
    assert es_admin("testop") is False


def test_admin_default(tmp_db):
    inicializar_db()
    assert validar_login("admin", "1234") is True
    assert es_admin("admin") is True
