from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from juntaai.logging_utils import configure_logging
from juntaai.ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)


def main() -> int:
    log_file = configure_logging()
    LOGGER.info("Inicializando aplicação")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.statusBar().showMessage(f"Logs em {log_file}")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
