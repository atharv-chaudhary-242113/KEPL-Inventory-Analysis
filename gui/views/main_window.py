# gui/views/main_window.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QLabel
from PyQt6.QtCore import Qt
from .file_selection_view import FileSelectionView
from .output_config_view import OutputConfigView
from .results_view import ResultsView
from .log_view import LogView
from .ml_training_view import MLTrainingView


class MainLayout(QWidget):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background-color: #1e1e2f; color: #ffffff;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("KEPL Analytics")
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 20px 10px; color: #4facfe;")
        sidebar_layout.addWidget(title)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #ffffff; color: #333333;")

        self.file_view = FileSelectionView(self.config)
        self.output_view = OutputConfigView(self.config, self)
        self.results_view = ResultsView()
        self.log_view = LogView()
        self.ml_view = MLTrainingView(self.config, self)

        self.content_stack.addWidget(self.file_view)     # Index 0
        self.content_stack.addWidget(self.output_view)   # Index 1
        self.content_stack.addWidget(self.results_view)  # Index 2
        self.content_stack.addWidget(self.log_view)      # Index 3
        self.content_stack.addWidget(self.ml_view)       # Index 4

        self.btn_files = self._create_nav_button("📁 File Setup", 0)
        self.btn_output = self._create_nav_button("⚙ Configure Output", 1)
        self.btn_ml = self._create_nav_button("🧠 Model Training", 4)
        self.btn_results = self._create_nav_button("📊 Run & Results", 2)
        self.btn_logs = self._create_nav_button("📝 Logs", 3)

        sidebar_layout.addWidget(self.btn_files)
        sidebar_layout.addWidget(self.btn_output)
        sidebar_layout.addWidget(self.btn_ml)
        sidebar_layout.addWidget(self.btn_results)
        sidebar_layout.addWidget(self.btn_logs)
        sidebar_layout.addStretch()

        layout.addWidget(sidebar)
        layout.addWidget(self.content_stack)

    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton { 
                text-align: left; padding: 15px 20px; font-size: 14px; 
                border: none; background-color: transparent; font-weight: bold;
            }
            QPushButton:hover { background-color: #2a2a40; color: #4facfe; }
        """)
        btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(index))
        return btn

    def show_results(self, results: dict) -> None:
        self.results_view.display_results(results)
        self.content_stack.setCurrentIndex(2)