# gui/views/results_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from gui.widgets.abc_chart_widget import ABCChartWidget


class ResultsView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Analysis Results")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #eef2f5; border-radius: 4px;")
        layout.addWidget(self.summary_label)

        self.chart = ABCChartWidget()
        layout.addWidget(self.chart)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #f9f9f9; background-color: #ffffff;")
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def display_results(self, results: dict) -> None:
        meta = results.get('summary_metadata', {})
        summary_text = "   |   ".join(f"<b>{k}:</b> {v}" for k, v in meta.items())
        self.summary_label.setText(summary_text)

        abc_df = results.get('abc_classification')
        if abc_df is not None and not abc_df.empty:
            self.chart.plot(abc_df)

            display_df = abc_df
            self.table.setColumnCount(len(display_df.columns))
            self.table.setRowCount(len(display_df))
            self.table.setHorizontalHeaderLabels(display_df.columns.astype(str))

            for row_idx, row in display_df.iterrows():
                for col_idx, val in enumerate(row):
                    item = QTableWidgetItem(str(val))
                    self.table.setItem(row_idx, col_idx, item)