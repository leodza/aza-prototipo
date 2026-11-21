"""Control de retencion para carpetas de rafagas."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RESULTS_LIMIT_BYTES = 40 * 1024**3


@dataclass(frozen=True)
class BurstFolder:
    path: Path
    size_bytes: int
    modified_time: float


def _path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0

    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() or child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def directory_size(path: str | Path) -> int:
    root = Path(path)
    if not root.is_dir():
        return 0
    return _path_size(root)


def list_burst_folders(root: str | Path) -> list[BurstFolder]:
    root_path = Path(root)
    if not root_path.is_dir():
        return []

    folders = []
    for path in root_path.rglob("Trigger_*"):
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            modified_time = path.stat().st_mtime
        except OSError:
            modified_time = 0.0
        folders.append(
            BurstFolder(
                path=path,
                size_bytes=_path_size(path),
                modified_time=modified_time,
            )
        )
    return sorted(folders, key=lambda item: (item.modified_time, str(item.path).lower()))


def cleanup_plan(root: str | Path, limit_bytes: int = DEFAULT_RESULTS_LIMIT_BYTES) -> tuple[int, list[BurstFolder]]:
    current_size = directory_size(root)
    if current_size <= limit_bytes:
        return current_size, []

    selected = []
    projected_size = current_size
    for folder in list_burst_folders(root):
        selected.append(folder)
        projected_size -= folder.size_bytes
        if projected_size <= limit_bytes:
            break
    return current_size, selected


def delete_burst_folders(folders: list[BurstFolder]) -> int:
    deleted_bytes = 0
    for folder in folders:
        if not folder.path.exists():
            continue
        shutil.rmtree(folder.path)
        deleted_bytes += folder.size_bytes
    return deleted_bytes
