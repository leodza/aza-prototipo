# database/models.py — Schema y migraciones
import sqlite3
import re
import logging
from src.core.config import DB_PATH

logger = logging.getLogger(__name__)

_VALID_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SQL_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\s+(DEFAULT|NOT|NULL|PRIMARY|KEY|AUTOINCREMENT|UNIQUE|CHECK|REFERENCES|\([^)]*\)|[0-9]+))*(,\s*[A-Za-z_][A-Za-z0-9_]*(\s+(DEFAULT|NOT|NULL|PRIMARY|KEY|AUTOINCREMENT|UNIQUE|CHECK|REFERENCES|\([^)]*\)|[0-9]+)))*$", re.IGNORECASE)


def _safe_name(name: str) -> str:
    if not _VALID_IDENTIFIER.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def _safe_type(name: str) -> str:
    if not _SQL_TYPE.match(name):
        raise ValueError(f"Invalid SQL type declaration: {name!r}")
    return name


def _add_column_if_missing(cur, table: str, col: str, coltype: str):
    table = _safe_name(table)
    col = _safe_name(col)
    coltype = _safe_type(coltype)
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def inicializar_db():
    logger.debug("DB PATH = %s", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracion_recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            min_tol REAL,
            max_tol REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            receta TEXT,
            estado TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        )
    """)

    _add_column_if_missing(cur, "usuarios", "is_admin", "INTEGER DEFAULT 0")
    _add_column_if_missing(cur, "registros", "angulo", "REAL")
    _add_column_if_missing(cur, "registros", "operador", "TEXT")
    _add_column_if_missing(cur, "registros", "lote", "TEXT")
    _add_column_if_missing(cur, "registros", "carpeta", "TEXT")

    cur.execute("SELECT COUNT(*) FROM usuarios")
    n = cur.fetchone()[0]
    if n == 0:
        from src.database.auth import _hash_pin
        cur.execute("""
            INSERT INTO usuarios(username, pin_hash, activo, is_admin)
            VALUES(?, ?, 1, 1)
        """, ("admin", _hash_pin("1234")))

    conn.commit()
    conn.close()
    logger.info("DB inicializada OK (registros incluye angulo/operador)")
