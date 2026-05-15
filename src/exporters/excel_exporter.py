# src/exporters/excel_exporter.py
"""
Excel Exporter module.

Serializes structural DataFrames to an Excel workbook via independent sheets.
"""

import pandas as pd
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ExcelExporter:
    """
    Class responsible for disk I/O and worksheet management from the results dictionary.
    """

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def export(self, results: dict[str, Any], output_path: str) -> None:
        """
        Execute the workbook generation and persistence protocol.

        Args:
            results (dict[str, Any]): The analytical payload containing all target dataframes.
            output_path (str): Target system location for the .xlsx file.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

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

                if 'abc_classification' in results and not results['abc_classification'].empty:
                    results['abc_classification'].to_excel(writer, sheet_name='ABC & Forecast', index=False)

                if 'exceptions' in results and not results['exceptions'].empty:
                    results['exceptions'].to_excel(writer, sheet_name='Delivery Exceptions', index=False)

                if 'anomaly_report' in results and not results['anomaly_report'].empty:
                    results['anomaly_report'].to_excel(writer, sheet_name='Price Anomalies', index=False)

                if 'monthly_breakdown' in results and not results['monthly_breakdown'].empty:
                    results['monthly_breakdown'].to_excel(writer, sheet_name='Monthly Breakdown', index=False)

            logger.info("Excel artifact successfully generated at: %s", output_path)

        except Exception as e:
            logger.error("Failed to execute Excel serialization: %s", str(e))
            raise