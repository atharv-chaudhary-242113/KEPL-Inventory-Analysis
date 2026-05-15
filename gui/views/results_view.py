# gui/views/results_view.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                              QTableWidgetItem, QHeaderView, QLineEdit, QHBoxLayout)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_font = QFont()
        header_font.setBold(True)
        self.table.horizontalHeader().setFont(header_font)

        # Excel-like selection behaviour
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)

        # Clicking a column header selects the whole column
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.table.selectColumn)

        # Clicking a row header selects the whole row
        self.table.verticalHeader().setSectionsClickable(True)
        self.table.verticalHeader().sectionClicked.connect(self.table.selectRow)

        # Add filter bar BEFORE layout.addWidget(self.table):
        self.filter_bar = QWidget()
        self.filter_layout = QHBoxLayout(self.filter_bar)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(1)
        self._filter_edits: list = []
        layout.addWidget(self.filter_bar)  # must come before table
        layout.addWidget(self.table)
        layout.addWidget(self.table)

    def display_results(self, results: dict) -> None:
        meta = results.get('summary_metadata', {})
        summary_text = "   |   ".join(f"<b>{k}:</b> {v}" for k, v in meta.items())
        self.summary_label.setText(summary_text)

        abc_df = results.get('abc_classification')
        if abc_df is not None and not abc_df.empty:
            self.chart.plot(abc_df)

            # Sort by total_value descending before display
            display_df = abc_df.sort_values('total_value', ascending=False).reset_index(drop=True)

            self.table.setSortingEnabled(False)  # disable during population to avoid index conflicts
            self.table.setColumnCount(len(display_df.columns))
            self.table.setRowCount(len(display_df))
            self.table.setHorizontalHeaderLabels(display_df.columns.astype(str))

            for row_idx, (_, row) in enumerate(display_df.iterrows()):
                for col_idx, val in enumerate(row):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

            # Autofit all columns to content
            self.table.resizeColumnsToContents()

            # Build filter bar to match current columns
            self._setup_filters(display_df.columns.tolist())

            # Re-enable sorting and sort by total_value
            self.table.setSortingEnabled(True)
            if 'total_value' in display_df.columns:
                tv_col = display_df.columns.tolist().index('total_value')
                self.table.sortItems(tv_col, Qt.SortOrder.DescendingOrder)

        def _setup_filters(self, columns: list) -> None:
            # Clear previous filter widgets
            while self.filter_layout.count():
                child = self.filter_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            self._filter_edits = []
            for col_name in columns:
                edit = QLineEdit()
                edit.setPlaceholderText(f'🔍 {col_name}')
                edit.setFixedHeight(24)
                edit.textChanged.connect(self._apply_filters)
                self.filter_layout.addWidget(edit)
                self._filter_edits.append(edit)

        def _apply_filters(self) -> None:
            active = [(c, e.text().lower()) for c, e in enumerate(self._filter_edits) if e.text()]
            for row in range(self.table.rowCount()):
                hidden = any(
                    (self.table.item(row, c) is None or f not in self.table.item(row, c).text().lower())
                    for c, f in active
                )
                self.table.setRowHidden(row, hidden)

    def _setup_filters(self, columns: list) -> None:
        # Clear previous filter widgets
        while self.filter_layout.count():
            child = self.filter_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._filter_edits = []
        for col_name in columns:
            edit = QLineEdit()
            edit.setPlaceholderText(f'🔍 {col_name}')
            edit.setFixedHeight(24)
            edit.textChanged.connect(self._apply_filters)
            self.filter_layout.addWidget(edit)
            self._filter_edits.append(edit)

    def _apply_filters(self) -> None:
        active = [(c, e.text().lower()) for c, e in enumerate(self._filter_edits) if e.text()]
        for row in range(self.table.rowCount()):
            hidden = any(
                (self.table.item(row, c) is None or f not in self.table.item(row, c).text().lower())
                for c, f in active
            )
            self.table.setRowHidden(row, hidden)