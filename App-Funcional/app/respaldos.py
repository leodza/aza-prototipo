# -*- coding: utf-8 -*-
"""Respaldos lógicos de la base de datos.

Genera un archivo JSON con el contenido de todas las tablas, lo guarda en
`data/respaldos` (y opcionalmente lo sube a S3), permite listarlos, compararlos
y restaurarlos.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from . import db

DIR = os.path.join(db.DATA_DIR, "respaldos")
VERSION = 1

MODELOS = {
    "roles": db.Rol,
    "usuarios": db.Usuario,
    "materiales": db.Material,
    "recetas": db.Receta,
    "lotes": db.Lote,
    "batches": db.Batch,
    "inspecciones": db.Inspeccion,
    "alarmas": db.Alarma,
    "auditoria": db.Auditoria,
    "configuracion": db.Configuracion,
}

# Orden de borrado (hijos primero) y de inserción (padres primero)
ORDEN_BORRADO = ["auditoria", "alarmas", "inspecciones", "batches", "lotes",
                 "recetas", "materiales", "usuarios", "roles", "configuracion"]
ORDEN_INSERCION = list(reversed(ORDEN_BORRADO))


def _valor(v):
    """Convierte a algo que JSON pueda guardar (Decimal, fechas, binarios)."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    return v


def _columnas(clase) -> list[str]:
    return [c.name for c in clase.__table__.columns]


def _fila(obj, clase) -> dict:
    return {c: _valor(getattr(obj, c)) for c in _columnas(clase)}


def _nombre_archivo(etiqueta: str) -> str:
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    limpio = "".join(c for c in (etiqueta or "manual").lower() if c.isalnum() or c in "-_")[:20]
    return f"respaldo-{sello}-{limpio or 'manual'}.json"


def _huella(datos: dict) -> str:
    crudo = json.dumps(datos, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(crudo).hexdigest()[:16]


def generar(etiqueta: str = "manual", subir: bool = True) -> dict:
    """Crea un respaldo y devuelve su descripción."""
    os.makedirs(DIR, exist_ok=True)
    with db.SesionLocal() as s:
        datos = {}
        for nombre, clase in MODELOS.items():
            filas = s.scalars(select(clase)).all()
            datos[nombre] = [_fila(f, clase) for f in filas]

    conteos = {k: len(v) for k, v in datos.items()}
    meta = {
        "version": VERSION,
        "generado": datetime.now(timezone.utc).isoformat(),
        "etiqueta": etiqueta,
        "motor": db.URL.split(":")[0],
        "conteos": conteos,
        "total": sum(conteos.values()),
        "huella": _huella(datos),
    }
    archivo = _nombre_archivo(etiqueta)
    ruta = os.path.join(DIR, archivo)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "datos": datos}, fh, ensure_ascii=False, indent=1)

    meta["archivo"] = archivo
    meta["bytes"] = os.path.getsize(ruta)
    if subir:
        try:
            from . import almacenamiento
            if almacenamiento.activo():
                almacenamiento.subir_archivo(ruta, f"respaldos/{archivo}",
                                             "application/json")
                meta["en_nube"] = True
        except Exception:                  # noqa: BLE001
            meta["en_nube"] = False
    return meta


def listar() -> list[dict]:
    if not os.path.isdir(DIR):
        return []
    salida = []
    for archivo in sorted(os.listdir(DIR), reverse=True):
        if not archivo.endswith(".json"):
            continue
        ruta = os.path.join(DIR, archivo)
        try:
            with open(ruta, encoding="utf-8") as fh:
                meta = json.load(fh).get("meta", {})
        except Exception:                  # noqa: BLE001
            continue
        meta["archivo"] = archivo
        meta["bytes"] = os.path.getsize(ruta)
        salida.append(meta)
    return salida


def leer(archivo: str) -> dict:
    ruta = os.path.join(DIR, os.path.basename(archivo))
    if not os.path.exists(ruta):
        raise FileNotFoundError(archivo)
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def ruta_de(archivo: str) -> str:
    return os.path.join(DIR, os.path.basename(archivo))


def comparar(a: str, b: str) -> dict:
    """Compara dos respaldos: conteos por tabla y diferencias."""
    uno, otro = leer(a), leer(b)
    filas = []
    for tabla in MODELOS:
        ca = len(uno["datos"].get(tabla, []))
        cb = len(otro["datos"].get(tabla, []))
        filas.append({"tabla": tabla, "a": ca, "b": cb, "diferencia": cb - ca})
    return {
        "a": {"archivo": a, "generado": uno["meta"].get("generado"),
              "huella": uno["meta"].get("huella"), "total": uno["meta"].get("total")},
        "b": {"archivo": b, "generado": otro["meta"].get("generado"),
              "huella": otro["meta"].get("huella"), "total": otro["meta"].get("total")},
        "tablas": filas,
        "iguales": uno["meta"].get("huella") == otro["meta"].get("huella"),
    }


def restaurar(datos_respaldo: dict) -> dict:
    """Reemplaza el contenido actual por el del respaldo."""
    if datos_respaldo.get("meta", {}).get("version") != VERSION:
        raise ValueError("La versión del respaldo no es compatible")
    datos = datos_respaldo.get("datos") or {}
    faltan = [t for t in MODELOS if t not in datos]
    if faltan:
        raise ValueError("El respaldo está incompleto: falta " + ", ".join(faltan))

    # La huella se calcula sobre los datos, sin la meta
    if datos_respaldo["meta"].get("huella") and \
            _huella(datos) != datos_respaldo["meta"]["huella"]:
        raise ValueError("El respaldo está alterado (la huella no coincide)")

    insertados = {}
    with db.SesionLocal() as s:
        for tabla in ORDEN_BORRADO:
            s.execute(MODELOS[tabla].__table__.delete())
        for tabla in ORDEN_INSERCION:
            clase = MODELOS[tabla]
            columnas = set(_columnas(clase))
            objetos = []
            for fila in datos[tabla]:
                limpia = {k: v for k, v in fila.items() if k in columnas}
                for campo, valor in list(limpia.items()):
                    if isinstance(valor, str) and valor[:4].isdigit() and "T" in valor:
                        try:
                            limpia[campo] = datetime.fromisoformat(valor)
                        except ValueError:
                            pass
                objetos.append(clase(**limpia))
            s.add_all(objetos)
            insertados[tabla] = len(objetos)
        s.commit()
    return insertados
