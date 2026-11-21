import sqlite3
import pytest
from src.database.models import inicializar_db, _safe_name, _safe_type


def test_inicializar_db_creates_tables(tmp_db):
    inicializar_db()
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()

    assert "configuracion_recetas" in tables
    assert "registros" in tables
    assert "usuarios" in tables


def test_inicializar_db_creates_admin(tmp_db):
    inicializar_db()
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin' AND is_admin=1")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1


def test_safe_name_valid():
    assert _safe_name("usuarios") == "usuarios"
    assert _safe_name("_test_col") == "_test_col"
    assert _safe_name("Configuracion_Recetas") == "Configuracion_Recetas"


def test_safe_name_invalid():
    with pytest.raises(ValueError):
        _safe_name("usuarios; DROP TABLE usuarios")
    with pytest.raises(ValueError):
        _safe_name("col-name")
    with pytest.raises(ValueError):
        _safe_name("123bad")


def test_safe_type_valid():
    assert _safe_type("TEXT") == "TEXT"
    assert _safe_type("INTEGER") == "INTEGER"
    assert _safe_type("REAL") == "REAL"
    assert _safe_type("INTEGER DEFAULT 0") == "INTEGER DEFAULT 0"
    assert _safe_type("TEXT NOT NULL") == "TEXT NOT NULL"


def test_safe_type_invalid():
    with pytest.raises(ValueError):
        _safe_type("TEXT; DROP TABLE usuarios")
    with pytest.raises(ValueError):
        _safe_type("'; DROP TABLE usuarios; --")


def test_registros_has_all_columns(tmp_db):
    inicializar_db()
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(registros)")
    cols = {r[1] for r in cur.fetchall()}
    conn.close()

    expected = {"fecha", "receta", "estado", "angulo", "operador", "lote", "carpeta"}
    assert expected.issubset(cols)
