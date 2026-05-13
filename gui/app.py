# gui/app.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from gui.views.main_window import MainLayout


class InventoryAnalyticsApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("KEPL Procurement Analytics")
        self.resize(1280, 800)
        self.config: dict = {}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout = MainLayout(self.config)
        layout.addWidget(self.main_layout)