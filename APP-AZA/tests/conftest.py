import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temporary database for each test."""
    db_file = str(tmp_path / "test.db")

    import src.core.config as config_mod
    import src.database.models as models_mod
    import src.database.auth as auth_mod

    monkeypatch.setattr(config_mod, "DB_PATH", db_file)
    monkeypatch.setattr(models_mod, "DB_PATH", db_file)
    monkeypatch.setattr(auth_mod, "DB_PATH", db_file)

    return db_file
