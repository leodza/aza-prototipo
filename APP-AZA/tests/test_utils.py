import os
from src.utils import resource_path
from src.core.logger import setup_logging


def test_resource_path_returns_string():
    result = resource_path(os.path.join("assets", "logo.png"))
    assert isinstance(result, str)
    assert result.endswith("logo.png")


def test_resource_path_absolute():
    result = resource_path(os.path.join("assets", "logo.png"))
    assert os.path.isabs(result)


def test_setup_logging_creates_handler():
    import logging
    setup_logging()
    logger = logging.getLogger()
    assert len(logger.handlers) > 0
