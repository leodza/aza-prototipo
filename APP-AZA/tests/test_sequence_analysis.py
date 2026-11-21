from pathlib import Path

import cv2
import numpy as np

from src.vision.sequence_analysis import (
    is_optimal_angle,
    is_sequence_folder,
    load_sequence,
)
from src.workers.sequence import SequenceBurstManager


def test_load_sequence_orders_frames_with_legacy_names(tmp_path):
    for name, value in (
        ("img_010.bmp", 10),
        ("img_002.png.bmp", 2),
        ("img_001.bmp", 1),
    ):
        cv2.imwrite(str(tmp_path / name), np.full((8, 8), value, dtype=np.uint8))

    frames = load_sequence(tmp_path)

    assert [int(frame[0, 0]) for frame in frames] == [1, 2, 10]


def test_trigger_folders_are_numbered_and_dated(tmp_path, monkeypatch):
    manager = SequenceBurstManager(str(tmp_path))
    monkeypatch.setattr("time.strftime", lambda fmt, now=None: {
        "%Y-%m-%d": "2026-06-10",
        "%Y%m%d_%H%M%S": "20260610_101530",
    }[fmt])

    first = manager._next_trigger_folder()
    second = manager._next_trigger_folder()

    assert first == Path(tmp_path) / "2026-06-10" / "Trigger_0001_20260610_101530"
    assert second == Path(tmp_path) / "2026-06-10" / "Trigger_0002_20260610_101530"


def test_trigger_counter_continues_from_existing_folders(tmp_path, monkeypatch):
    existing = tmp_path / "2026-06-10" / "Trigger_0042_20260610_101500"
    existing.mkdir(parents=True)
    manager = SequenceBurstManager(str(tmp_path))
    monkeypatch.setattr("time.strftime", lambda fmt, now=None: {
        "%Y-%m-%d": "2026-06-10",
        "%Y%m%d_%H%M%S": "20260610_101530",
    }[fmt])

    folder = manager._next_trigger_folder()

    assert folder == Path(tmp_path) / "2026-06-10" / "Trigger_0043_20260610_101530"


def test_only_first_quadrant_is_optimal():
    assert is_optimal_angle(0.0)
    assert is_optimal_angle(45.0)
    assert is_optimal_angle(90.0)
    assert not is_optimal_angle(90.1)
    assert not is_optimal_angle(180.0)
    assert not is_optimal_angle(359.9)


def test_sequence_folder_requires_at_least_two_bmp_images(tmp_path):
    assert not is_sequence_folder(tmp_path)

    cv2.imwrite(str(tmp_path / "img_001.bmp"), np.zeros((8, 8), dtype=np.uint8))
    assert not is_sequence_folder(tmp_path)

    cv2.imwrite(str(tmp_path / "img_002.bmp"), np.zeros((8, 8), dtype=np.uint8))
    assert is_sequence_folder(tmp_path)
