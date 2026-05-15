# gui/views/ml_training_view.py
import logging
from pathlib import Path
import gc

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal

from src.pipeline import AnalysisPipeline, PipelineConfig
from src.processors.time_series_trainer import TimeSeriesTrainer

logger = logging.getLogger(__name__)


class MLTrainingWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        self.models_dir = Path(__file__).resolve().parent.parent.parent / 'models'

    def run(self) -> None:
        try:
            is_lite_mode = self.config.get('is_lite_mode', True)
            pipeline_config = PipelineConfig(is_lite_mode=is_lite_mode)

            self.progress.emit("Initializing shared data preparation layer...")
            pipeline = AnalysisPipeline(self.config)

            self.progress.emit("Running batched data ingestion & NLP semantic deduplication...")
            clean_datasets = pipeline.prepare_clean_data(pipeline_config)
            clean_pv_df = clean_datasets['PV']

            self.progress.emit(f"Initiating Time-Series Analysis across {len(clean_pv_df)} standardized records...")
            trainer = TimeSeriesTrainer(min_months=6)

            metrics = trainer.train_models(clean_pv_df, self.models_dir)

            # Immediate explicit memory reclamation for 4GB constraints
            pipeline_config.reclaim_memory(clean_datasets, clean_pv_df)

            self.finished.emit(metrics)
        except Exception as e:
            self.error.emit(str(e))


class MLTrainingView(QWidget):
    def __init__(self, config: dict, main_layout) -> None:
        super().__init__()
        self.config = config
        self.main_layout = main_layout
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Machine Learning Control Protocol")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        info = QLabel(
            "Initiate autoregressive model fitting on semantically deduplicated datasets. "
            "Chronological splits and MAE validation are strictly enforced. Inferior models are discarded.")
        info.setStyleSheet("font-size: 14px; margin-bottom: 20px; color: #555;")
        layout.addWidget(info)

        self.run_btn = QPushButton("▶ Execute XGBoost Training Sequence")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #8A2BE2; color: white; padding: 15px; 
                font-weight: bold; font-size: 16px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #9B30FF; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        self.run_btn.clicked.connect(self.start_training)
        layout.addWidget(self.run_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        layout.addWidget(self.log_output)

    def start_training(self) -> None:
        self.main_layout.file_view.update_config()

        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_output.append("Initializing worker thread with low-memory constraints...\n")

        self.worker = MLTrainingWorker(self.config)
        self.worker.progress.connect(self.log_output.append)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_success(self, metrics: dict) -> None:
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        summary = (f"\n[EXECUTION COMPLETE]\n"
                   f"Entities Processed: {metrics.get('total_processed')}\n"
                   f"Skipped (Sparsity < 6mo): {metrics.get('skipped_sparsity')}\n"
                   f"Failed MAE Validation: {metrics.get('failed_validation')}\n"
                   f"Persisted Superior Models: {metrics.get('models_persisted')}\n")
        self.log_output.append(summary)

    def on_error(self, err_msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log_output.append(f"\n[CRITICAL FAILURE]: {err_msg}")
        QMessageBox.critical(self, "Training Error", f"Execution Failed:\n{err_msg}")