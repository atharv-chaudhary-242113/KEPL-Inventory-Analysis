# src/exporters/excel_exporter.py
from typing import Dict
import pandas as pd
import logging
from .base_exporter import BaseExporter

logger = logging.getLogger("kepl_pipeline")


class ExcelExporter(BaseExporter):
    """
    Concrete implementation handling Excel multi-sheet generation.
    """

    def export(self, results: Dict[str, pd.DataFrame], output_path: str) -> None:
        """
        Writes dataframes to independent Excel sheets using openpyxl engine.

        Args:
            results (Dict[str, pd.DataFrame]): Processed dataframes mapping.
            output_path (str): Target output file path (.xlsx).
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for sheet_name, df in results.items():
                    if df is not None and not df.empty:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        logger.debug(f"Wrote sheet: {sheet_name}")
            logger.info(f"Successfully exported analysis to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export Excel to {output_path}. Error: {str(e)}")
            raise