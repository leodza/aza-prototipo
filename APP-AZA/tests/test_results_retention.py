import os

from src.results_retention import cleanup_plan, delete_burst_folders, directory_size


def _make_burst(path, size, modified_time):
    path.mkdir(parents=True)
    (path / "img_001.bmp").write_bytes(b"x" * size)
    os.utime(path, (modified_time, modified_time))


def test_cleanup_plan_selects_oldest_bursts_until_under_limit(tmp_path):
    root = tmp_path / "results"
    old = root / "2026-06-10" / "Trigger_0001_20260610_101530"
    middle = root / "2026-06-10" / "Trigger_0002_20260610_101630"
    newest = root / "2026-06-10" / "Trigger_0003_20260610_101730"
    _make_burst(old, 40, 10)
    _make_burst(middle, 35, 20)
    _make_burst(newest, 30, 30)

    current_size, folders = cleanup_plan(root, limit_bytes=50)

    assert current_size == 105
    assert [folder.path for folder in folders] == [old, middle]


def test_cleanup_plan_returns_no_folders_when_under_limit(tmp_path):
    root = tmp_path / "results"
    _make_burst(root / "2026-06-10" / "Trigger_0001_20260610_101530", 40, 10)

    current_size, folders = cleanup_plan(root, limit_bytes=50)

    assert current_size == 40
    assert folders == []


def test_delete_burst_folders_removes_selected_directories(tmp_path):
    root = tmp_path / "results"
    old = root / "2026-06-10" / "Trigger_0001_20260610_101530"
    keep = root / "2026-06-10" / "Trigger_0002_20260610_101630"
    _make_burst(old, 40, 10)
    _make_burst(keep, 35, 20)
    _current_size, folders = cleanup_plan(root, limit_bytes=50)

    deleted_bytes = delete_burst_folders(folders)

    assert deleted_bytes == 40
    assert not old.exists()
    assert keep.exists()
    assert directory_size(root) == 35
