# gui/widgets/folder_picker.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog


class FolderPicker(QWidget):
    def __init__(self, label_text: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        self.label = QLabel(label_text)
        self.label.setFixedWidth(200)
        self.label.setStyleSheet("font-weight: bold;")

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setStyleSheet("padding: 8px 15px; background-color: #e0e0e0; border: none; border-radius: 4px;")
        self.browse_btn.clicked.connect(self._browse)

        layout.addWidget(self.label)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_btn)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.path_edit.setText(path)

    def get_path(self) -> str:
        return self.path_edit.text()