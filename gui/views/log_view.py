# gui/views/log_view.py
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import QTimer


class LogView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            background-color: #1e1e1e; color: #d4d4d4; 
            font-family: Consolas, monospace; font-size: 13px; padding: 10px;
        """)
        layout.addWidget(self.text_edit)

        self.log_path = Path(__file__).resolve().parent.parent.parent / 'logs' / 'app.log'
        self._log_offset = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    def refresh(self) -> None:
        if not self.log_path.exists():
            return
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                f.seek(self._log_offset)
                new_data = f.read()
                if new_data:
                    self.text_edit.append(new_data.strip())
                    self.text_edit.verticalScrollBar().setValue(self.text_edit.verticalScrollBar().maximum())
                    self._log_offset = f.tell()
        except Exception:
            pass