# src/loaders/base_loader.py
"""
Abstract base loader module.
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB limit

    @abstractmethod
    def load(self, filepath: str) -> pd.DataFrame | None:
        pass

    def _validate_file_size(self, filepath: str) -> None:
        size: int = os.path.getsize(filepath)
        if size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File {filepath} exceeds 5 MB ({size} bytes). "
                "Export a smaller date range."
            )

    @staticmethod
    def downcast_memory(df: pd.DataFrame) -> pd.DataFrame:
        """Compresses 64-bit data structures to 32/16-bit to prevent initial OOM."""
        for col in df.columns:
            col_type = df[col].dtype

            if col_type == object:
                num_unique_values = len(df[col].unique())
                num_total_values = len(df[col])
                if num_total_values > 0 and num_unique_values / num_total_values < 0.5:
                    df[col] = df[col].astype('category')
            elif pd.api.types.is_float_dtype(col_type):
                df[col] = pd.to_numeric(df[col], downcast='float')
            elif pd.api.types.is_integer_dtype(col_type):
                df[col] = pd.to_numeric(df[col], downcast='integer')

        return df

    def _parse_tally_export(self, filepath: str) -> pd.DataFrame:
        self._validate_file_size(filepath)
        filename: str = Path(filepath).name
        logger.debug("Reading file: %s", filename)

        df: pd.DataFrame = pd.read_csv(filepath, skiprows=6)

        fill_cols: list[str] = ['Date', 'Vch/Bill No', 'Particulars']
        available_fill_cols: list[str] = [col for col in fill_cols if col in df.columns]
        if available_fill_cols:
            df[available_fill_cols] = df[available_fill_cols].ffill()

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

        num_cols: list[str] = ['Qty.', 'Price', 'Amount']
        for col in num_cols:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'Unit' in df.columns:
            df = df[df['Unit'] != '-']

        if 'Item Details' in df.columns:
            exclusion_pattern: str = 'freight|tax|charge'
            mask: pd.Series = df['Item Details'].astype(str).str.lower().str.contains(exclusion_pattern, na=False)
            df = df[~mask]

        df = self.downcast_memory(df)
        return df