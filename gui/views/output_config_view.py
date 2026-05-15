# gui/views/output_config_view.py
import os
import traceback
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QHBoxLayout, QCheckBox
from PyQt6.QtCore import QThread, pyqtSignal
from gui.widgets.folder_picker import FolderPicker
from src.pipeline import AnalysisPipeline


class PipelineWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        try:
            pipeline = AnalysisPipeline(self.config)
            results = pipeline.run()
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")


class OutputConfigView(QWidget):
    def __init__(self, config: dict, main_layout) -> None:
        super().__init__()
        self.config = config
        self.main_layout = main_layout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Configure Output")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 30px;")
        layout.addWidget(title)

        self.folder_picker = FolderPicker("Output Directory")
        layout.addWidget(self.folder_picker)

        name_layout = QHBoxLayout()
        name_label = QLabel("Output Filename")
        name_label.setFixedWidth(200)
        name_label.setStyleSheet("font-weight: bold;")
        self.name_edit = QLineEdit("report_output.xlsx")
        self.name_edit.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        growth_layout = QHBoxLayout()
        growth_label = QLabel("Expected Annual Growth (%)")
        growth_label.setFixedWidth(200)
        growth_label.setStyleSheet("font-weight: bold;")
        self.growth_edit = QLineEdit("30")
        self.growth_edit.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        growth_layout.addWidget(growth_label)
        growth_layout.addWidget(self.growth_edit)
        layout.addLayout(growth_layout)

        layout.addSpacing(10)
        self.ml_checkbox = QCheckBox("Enable ML Time-Series Forecasting (Inference Phase)")
        self.ml_checkbox.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.ml_checkbox)

        layout.addSpacing(20)
        self.run_btn = QPushButton("▶ Run Analysis")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4facfe; color: white; padding: 15px; 
                font-weight: bold; font-size: 16px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #00f2fe; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        self.run_btn.clicked.connect(self.run_pipeline)
        layout.addWidget(self.run_btn)
        layout.addStretch()

    def run_pipeline(self) -> None:
        self.main_layout.file_view.update_config()

        out_dir = self.folder_picker.get_path()
        if not out_dir:
            QMessageBox.warning(self, "Validation Error", "Select an output directory.")
            return

        self.config['output_path'] = os.path.join(out_dir, self.name_edit.text())
        self.config['use_ml_forecast'] = self.ml_checkbox.isChecked()

        try:
            growth_input = self.growth_edit.text().strip()
            growth_val = float(growth_input) if growth_input else 30.0
            self.config['growth_rate'] = 1.0 + (growth_val / 100.0)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Growth must be a numerical percentage.")
            return

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running Pipeline...")

        self.worker = PipelineWorker(self.config)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_success(self, results: dict) -> None:
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run Analysis")
        self.main_layout.show_results(results)

    def on_error(self, err_msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶ Run Analysis")
        QMessageBox.critical(self, "Pipeline Error", f"Execution Failed:\n{err_msg}")