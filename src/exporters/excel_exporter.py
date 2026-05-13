# src/exporters/excel_exporter.py
"""
Excel Exporter module.

Generates formatted multi-sheet Excel workbooks from analytical results.
Applies injection sanitisation, Indian numerical formatting, and conditional styling.
"""

import logging
from typing import Any

import pandas as pd
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font
from openpyxl.worksheet.worksheet import Worksheet

from .base_exporter import BaseExporter
from src.processors.data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class ExcelExporter(BaseExporter):
    """
    Concrete exporter utilizing openpyxl to generate structured xlsx reports.
    Executes automated data sanitisation to prevent spreadsheet application injection attacks.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the Excel exporter.

        Args:
            config (dict[str, Any] | None): Configuration mapping. Expected to
                                            contain the 'include_anomaly_report' flag.
        """
        self.config: dict[str, Any] = config or {}
        self.include_anomaly_report: bool = self.config.get('include_anomaly_report', True)

    def export(self, results: dict[str, Any], output_path: str) -> None:
        """
        Execute the workbook generation and persistence protocol.

        Args:
            results (dict[str, Any]): The analytical payload containing all target dataframes.
            output_path (str): Target system location for the .xlsx file.
        """
        logger.info("Initiating Excel export to %s", output_path)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            if 'summary_metadata' in results:
                self._write_summary_sheet(writer, results['summary_metadata'])

            if 'abc_classification' in results:
                df_abc = DataCleaner.sanitise_for_export(results['abc_classification'])
                df_abc.to_excel(writer, sheet_name='ABC Classification', index=False)
                self._format_abc_sheet(writer.sheets['ABC Classification'])

            if 'monthly_forecast' in results:
                df_mf = DataCleaner.sanitise_for_export(results['monthly_forecast'])
                df_mf.to_excel(writer, sheet_name='Monthly Forecast', index=False)
                self._format_forecast_sheet(writer.sheets['Monthly Forecast'])

            if 'quarterly_forecast' in results:
                df_qf = DataCleaner.sanitise_for_export(results['quarterly_forecast'])
                df_qf.to_excel(writer, sheet_name='Quarterly Forecast', index=False)
                self._format_forecast_sheet(writer.sheets['Quarterly Forecast'])

            if 'monthly_breakdown' in results:
                df_mb = DataCleaner.sanitise_for_export(results['monthly_breakdown'])
                df_mb.to_excel(writer, sheet_name='Monthly Breakdown', index=False)
                self._format_generic_sheet(writer.sheets['Monthly Breakdown'])

            if 'lead_times' in results:
                df_lt = DataCleaner.sanitise_for_export(results['lead_times'])
                df_lt.to_excel(writer, sheet_name='Lead Times', index=False)
                self._format_generic_sheet(writer.sheets['Lead Times'])

            if self.include_anomaly_report and 'anomaly_report' in results:
                df_ar = DataCleaner.sanitise_for_export(results['anomaly_report'])
                df_ar.to_excel(writer, sheet_name='Anomaly Report', index=False)
                self._format_generic_sheet(writer.sheets['Anomaly Report'])

            raw_sheets = {
                'Raw GRN': 'raw_grn',
                'Raw POV': 'raw_pov',
                'Raw PV': 'raw_pv'
            }

            for sheet_name, key in raw_sheets.items():
                if key in results:
                    df_raw = DataCleaner.sanitise_for_export(results[key])
                    df_raw.to_excel(writer, sheet_name=sheet_name, index=False)
                    self._format_generic_sheet(writer.sheets[sheet_name])

        logger.info("Excel export completed successfully.")

    def _write_summary_sheet(self, writer: pd.ExcelWriter, metadata: dict[str, Any]) -> None:
        """
        Generate the Executive Summary sheet including mandatory caveats.

        Args:
            writer (pd.ExcelWriter): Openpyxl writer instance.
            metadata (dict[str, Any]): Run execution metrics and temporal boundaries.
        """
        df_meta = pd.DataFrame(list(metadata.items()), columns=['Metric', 'Value'])
        df_meta.to_excel(writer, sheet_name='Summary', index=False)
        ws = writer.sheets['Summary']

        ws.append([])
        ws.append(['Plain Language Interpretation:'])
        ws.append([
            'These estimates are based on purchase data only (no closing stock available). '
            'If you have historical closing stock data, add it via the Closing Stock file picker '
            'to improve accuracy.'
        ])

        self._format_generic_sheet(ws)

    def _format_generic_sheet(self, ws: Worksheet) -> None:
        """
        Apply structural worksheet standards: freeze top row, apply auto-filter bounds.

        Args:
            ws (Worksheet): Target openpyxl worksheet.
        """
        if ws.max_row > 1 and ws.max_column > 0:
            ws.freeze_panes = 'A2'
            max_col_letter = get_column_letter(ws.max_column)
            ws.auto_filter.ref = f"A1:{max_col_letter}{ws.max_row}"
        self._apply_indian_number_format(ws)

    def _format_abc_sheet(self, ws: Worksheet) -> None:
        """
        Apply Pareto-specific layout elements: conditional row coloring based on class.

        Args:
            ws (Worksheet): ABC Classification worksheet.
        """
        self._format_generic_sheet(ws)

        fill_a = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        fill_b = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        fill_c = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

        header = [cell.value for cell in ws[1]]
        class_idx = header.index('abc_class') + 1 if 'abc_class' in header else None

        if class_idx:
            for row in range(2, ws.max_row + 1):
                abc_val = ws.cell(row=row, column=class_idx).value
                if abc_val == 'A':
                    target_fill = fill_a
                elif abc_val == 'B':
                    target_fill = fill_b
                elif abc_val == 'C':
                    target_fill = fill_c
                else:
                    continue

                for col in range(1, ws.max_column + 1):
                    ws.cell(row=row, column=col).fill = target_fill

    def _format_forecast_sheet(self, ws: Worksheet) -> None:
        """
        Apply forecasting layout constraints, bolding reorder quantity outputs.

        Args:
            ws (Worksheet): Target forecast worksheet.
        """
        self._format_generic_sheet(ws)

        header = [cell.value for cell in ws[1]]
        target_cols = [i + 1 for i, v in enumerate(header) if v and 'reorder_qty' in str(v).lower()]

        bold_font = Font(bold=True)
        for col_idx in target_cols:
            for row in range(1, ws.max_row + 1):
                ws.cell(row=row, column=col_idx).font = bold_font

    def _apply_indian_number_format(self, ws: Worksheet) -> None:
        """
        Force locale-specific numerical rendering (e.g., 1,00,000) for integer and float cells.

        Args:
            ws (Worksheet): Target worksheet.
        """
        indian_format = '[>=100000]##\\,##\\,##0;[>=1000]##\\,##0;0'

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = indian_format