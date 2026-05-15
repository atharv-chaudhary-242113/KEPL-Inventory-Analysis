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
        Write analytical metrics and operational exceptions to respective sheets.

        Args:
            results (dict[str, Any]): Consolidated pipeline payloads.
            output_path (str): Destination file path.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                if 'lead_times' in results and not results['lead_times'].empty:
                    results['lead_times'].to_excel(writer, sheet_name='Lead Time Stats', index=False)

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