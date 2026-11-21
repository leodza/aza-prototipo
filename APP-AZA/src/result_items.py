"""Helpers para construir elementos visibles de resultados."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _frame_number(path: Path) -> int:
    match = re.search(r"img_(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _sequence_frame_path(folder: Path, frame_number: int) -> str | None:
    for path in sorted(folder.glob("img_*.bmp"), key=_frame_number):
        if _frame_number(path) == frame_number:
            return str(path)
    return None


def result_item_for(result_path: str | Path) -> dict[str, Any]:
    """Devuelve un resultado y, si aplica, el frame usado para medir angulo."""
    path = Path(result_path)
    item: dict[str, Any] = {
        "result": str(path),
        "frame": None,
    }
    metrics_path = path.parent / "metricas.json"
    if not metrics_path.is_file():
        return item

    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return item

    if metrics.get("exit_angle_deg") is None:
        return item
    try:
        angle_frame = int(metrics["angle_frame"])
    except (KeyError, TypeError, ValueError):
        return item

    item["frame"] = _sequence_frame_path(path.parent, angle_frame)
    return item
