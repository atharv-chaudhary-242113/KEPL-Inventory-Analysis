# run_gui.py
import sys
from PyQt6.QtWidgets import QApplication
from gui.app import InventoryAnalyticsApp

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = InventoryAnalyticsApp()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()