import os

# APP-AZA/ (parent of src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# If running as module, __file__ is inside src/, so one dirname up is root
# But if __file__ is src/core/config.py, two dirs up goes to APP-AZA/
# Verify: if we're actually at src/, go up one more level
if os.path.basename(BASE_DIR) == "src":
    BASE_DIR = os.path.dirname(BASE_DIR)

DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "analisis_datos.db")

DEVICE_ID_DEFAULT = "devicemodul00_06_be_12_63_d4"
GENTL_DIR_DEFAULT = "/opt/baumer-camera-explorer/lib"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


WEB_MONITOR_ENABLED = _env_bool("AZA_WEB_MONITOR", True)
WEB_MONITOR_HOST = os.getenv("AZA_WEB_MONITOR_HOST", "0.0.0.0")
WEB_MONITOR_PORT = _env_int("AZA_WEB_MONITOR_PORT", 8080)
WEB_MONITOR_SCREEN = _env_int("AZA_WEB_MONITOR_SCREEN", 0)
WEB_MONITOR_FPS = _env_int("AZA_WEB_MONITOR_FPS", 5)
WEB_MONITOR_JPEG_QUALITY = _env_int("AZA_WEB_MONITOR_JPEG_QUALITY", 70)
