from datetime import datetime

import pytest

from src.results_export import delete_result_path, export_results


def test_export_results_copies_complete_tree(tmp_path):
    source = tmp_path / "results"
    trigger = source / "2026-06-10" / "Trigger_0001_20260610_101530"
    trigger.mkdir(parents=True)
    (trigger / "resultado_analisis.png").write_bytes(b"png")
    (trigger / "metricas.json").write_text('{"angle": 45}', encoding="utf-8")
    destination = tmp_path / "usb"

    exported = export_results(
        source,
        destination,
        now=datetime(2026, 6, 10, 10, 15, 30),
    )

    assert exported.name == "AZA_Resultados_20260610_101530"
    copied_trigger = exported / "2026-06-10" / trigger.name
    assert (copied_trigger / "resultado_analisis.png").read_bytes() == b"png"
    assert (copied_trigger / "metricas.json").is_file()


def test_export_results_rejects_destination_inside_source(tmp_path):
    source = tmp_path / "results"
    source.mkdir()
    (source / "resultado_analisis.png").write_bytes(b"png")

    with pytest.raises(RuntimeError, match="dentro"):
        export_results(source, source / "usb")


def test_delete_result_path_removes_file_inside_results(tmp_path):
    root = tmp_path / "results"
    root.mkdir()
    target = root / "resultado_analisis.png"
    target.write_bytes(b"png")

    deleted = delete_result_path(root, target)

    assert deleted == target
    assert not target.exists()


def test_delete_result_path_removes_folder_inside_results(tmp_path):
    root = tmp_path / "results"
    target = root / "2026-06-10" / "Trigger_0001"
    target.mkdir(parents=True)
    (target / "img_001.bmp").write_bytes(b"bmp")

    deleted = delete_result_path(root, target)

    assert deleted == target
    assert not target.exists()


def test_delete_result_path_rejects_results_root(tmp_path):
    root = tmp_path / "results"
    root.mkdir()

    with pytest.raises(RuntimeError, match="raiz"):
        delete_result_path(root, root)


def test_delete_result_path_rejects_path_outside_results(tmp_path):
    root = tmp_path / "results"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeError, match="dentro"):
        delete_result_path(root, outside)

    assert outside.exists()
