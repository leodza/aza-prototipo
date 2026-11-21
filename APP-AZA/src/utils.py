import os
import sys


def resource_path(rel_path: str) -> str:
    """Devuelve la ruta correcta tanto en dev como en PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    from src.core.config import BASE_DIR
    return os.path.join(BASE_DIR, rel_path)
