from __future__ import annotations

import logging
from pathlib import Path

from juntaai.config import get_log_file


def configure_logging() -> Path:
    log_file = get_log_file()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
        force=True,
    )
    logging.getLogger(__name__).info("Logging inicializado em %s", log_file)
    return log_file
