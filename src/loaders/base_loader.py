# src/loaders/base_loader.py
"""
Abstract base loader module.

Defines the contract for all data ingestion classes and implements
shared parsing logic for Tally-exported CSV formats.
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """
    Abstract base class defining the required interface for all dataset loaders.

    Implements common validation and structural parsing mechanisms to ensure
    DRY principles across specific document handlers.
    """

    MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB limit

    @abstractmethod
    def load(self, filepath: str) -> pd.DataFrame | None:
        """
        Load and process the target dataset.

        Args:
            filepath (str): Absolute or relative path to the input CSV file.

        Returns:
            pd.DataFrame | None: Cleaned dataframe containing the dataset,
            or None if no file path is provided.
        """
        pass

    def _validate_file_size(self, filepath: str) -> None:
        """
        Validate that the target file does not exceed maximum acceptable memory footprint.

        Args:
            filepath (str): Path to the target file.

        Raises:
            ValueError: If the file size exceeds MAX_FILE_SIZE_BYTES limit.
        """
        size: int = os.path.getsize(filepath)
        if size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File {filepath} exceeds 5 MB ({size} bytes). "
                "Export a smaller date range."
            )

    def _parse_tally_export(self, filepath: str) -> pd.DataFrame:
        """
        Parse a standard Tally CSV export format into a normalized DataFrame.

        Skips metadata headers, forward-fills voucher identity columns,
        standardizes date objects, casts numerical types, and drops non-material rows.

        Args:
            filepath (str): Path to the CSV file.

        Returns:
            pd.DataFrame: Normalized and cleaned dataset.
        """
        self._validate_file_size(filepath)
        filename: str = Path(filepath).name
        logger.debug("Reading file: %s", filename)

        # Skip top 6 rows containing non-tabular Tally metadata
        df: pd.DataFrame = pd.read_csv(filepath, skiprows=6)

        # Forward-fill primary identifying columns within each voucher block
        fill_cols: list[str] = ['Date', 'Vch/Bill No', 'Particulars']
        available_fill_cols: list[str] = [col for col in fill_cols if col in df.columns]
        if available_fill_cols:
            df[available_fill_cols] = df[available_fill_cols].ffill()

        # Standardize date types for time-series operations
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

        # Clean string numerics and cast to float
        num_cols: list[str] = ['Qty.', 'Price', 'Amount']
        for col in num_cols:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Filter out structural visual breaks
        if 'Unit' in df.columns:
            df = df[df['Unit'] != '-']

        # Filter non-material transactional rows
        if 'Item Details' in df.columns:
            exclusion_pattern: str = 'freight|tax|charge'
            mask: pd.Series = df['Item Details'].astype(str).str.lower().str.contains(exclusion_pattern, na=False)
            df = df[~mask]

        return df