# src/loaders/closing_stock_loader.py
"""Closing Stock dataset loader module."""

import logging
import pandas as pd

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class ClosingStockLoader(BaseLoader):
    """
    Loader class responsible for processing inventory Closing Stock data.

    Acts as an Open/Closed Principle (OCP) extension point. Configured to handle
    multiple time frequencies once the external dataset becomes available.
    """

    def __init__(self, frequency: str = 'monthly') -> None:
        """
        Initialize the Closing Stock Loader.

        Args:
            frequency (str): The time frequency of the target stock data.
                             Must be 'daily', 'weekly', 'monthly', or 'quarterly'.

        Raises:
            ValueError: If an unsupported frequency type is provided.
        """
        valid_frequencies: set[str] = {'daily', 'weekly', 'monthly', 'quarterly'}
        if frequency not in valid_frequencies:
            raise ValueError(f"Invalid frequency. Must be one of: {valid_frequencies}")
        self.frequency: str = frequency

    def load(self, filepath: str | None = None) -> pd.DataFrame | None:
        """
        Load and normalize the closing stock dataset.

        Args:
            filepath (str | None): Path to the Closing Stock CSV file.

        Returns:
            pd.DataFrame | None: Processed dataframe matching the schema
            (Item Details, Particulars, Period, Closing Qty), or None if omitted.
        """
        if not filepath:
            return None

        self._validate_file_size(filepath)

        # Stub logic. Requires structural implementation upon data availability.
        logger.warning("ClosingStockLoader stub called for frequency: %s", self.frequency)

        return None