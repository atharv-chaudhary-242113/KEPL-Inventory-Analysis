# run_gui.py
import sys
import logging

# Initialize logging absolutely first to establish primacy over library defaults
from src.logger_config import setup_logger
setup_logger()

from PyQt6.QtWidgets import QApplication
from gui.app import InventoryAnalyticsApp


def main() -> None:
    logger = logging.getLogger(__name__)
    logger.info("Application starting...")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = InventoryAnalyticsApp()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()