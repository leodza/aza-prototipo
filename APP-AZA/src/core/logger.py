import os
import sys
import logging


def setup_logging(level=logging.INFO):
    """Configura logging con archivo y consola."""
    from src.core.config import BASE_DIR
    log_file = os.path.join(BASE_DIR, "app.log")
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
