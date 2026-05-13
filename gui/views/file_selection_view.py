# gui/views/file_selection_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from gui.widgets.file_picker import FilePicker


class FileSelectionView(QWidget):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Input File Setup")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 30px;")
        layout.addWidget(title)

        self.pov_picker = FilePicker("Purchase Order Vouchers")
        self.grn_picker = FilePicker("Goods Received Notes")
        self.pv_picker = FilePicker("Purchase Vouchers")
        self.cs_picker = FilePicker("Closing Stock (Optional)")

        layout.addWidget(self.pov_picker)
        layout.addWidget(self.grn_picker)
        layout.addWidget(self.pv_picker)
        layout.addWidget(self.cs_picker)
        layout.addStretch()

    def update_config(self) -> None:
        self.config['pov_path'] = self.pov_picker.get_path()
        self.config['grn_path'] = self.grn_picker.get_path()
        self.config['pv_path'] = self.pv_picker.get_path()
        self.config['closing_stock_path'] = self.cs_picker.get_path()