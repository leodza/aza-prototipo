"""Exportacion de resultados a una carpeta elegida por el operador."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def _resolve_inside(root: str | Path, target: str | Path) -> tuple[Path, Path]:
    root_path = Path(root).expanduser().resolve()
    target_path = Path(target).expanduser().resolve()
    if target_path == root_path:
        raise RuntimeError("No se puede borrar el directorio raiz de resultados")
    if root_path not in target_path.parents:
        raise RuntimeError("Solo se pueden borrar archivos o carpetas dentro del directorio de resultados")
    return root_path, target_path


def delete_result_path(root: str | Path, target: str | Path) -> Path:
    _root_path, target_path = _resolve_inside(root, target)

    if not target_path.exists():
        raise RuntimeError("La ruta seleccionada no existe")
    if target_path.is_symlink() or target_path.is_file():
        target_path.unlink()
    elif target_path.is_dir():
        shutil.rmtree(target_path)
    else:
        raise RuntimeError("La ruta seleccionada no es un archivo ni una carpeta")
    return target_path


def export_results(
    source: str | Path,
    destination_root: str | Path,
    now: datetime | None = None,
) -> Path:
    source_path = Path(source).resolve()
    destination_path = Path(destination_root).resolve()

    if not source_path.is_dir():
        raise RuntimeError("El directorio de resultados no existe")
    if not any(source_path.rglob("resultado_analisis.png")):
        raise RuntimeError("No hay resultados de analisis para descargar")
    if destination_path == source_path or source_path in destination_path.parents:
        raise RuntimeError("El destino no puede estar dentro del directorio de resultados")

    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    export_path = destination_path / f"AZA_Resultados_{timestamp}"
    suffix = 1
    while export_path.exists():
        export_path = destination_path / f"AZA_Resultados_{timestamp}_{suffix:02d}"
        suffix += 1

    destination_path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, export_path)
    return export_path
