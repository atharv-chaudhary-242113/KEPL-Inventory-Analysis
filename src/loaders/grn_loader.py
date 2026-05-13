# src/loaders/grn_loader.py
"""Goods Received Note (GRN) dataset loader module."""

import pandas as pd

from .base_loader import BaseLoader


class GRNLoader(BaseLoader):
    """
    Loader class responsible for processing Goods Received Notes.
    """

    def load(self, filepath: str) -> pd.DataFrame:
        """
        Load and normalize the GRN dataset.

        Args:
            filepath (str): Path to the GRN CSV file.

        Returns:
            pd.DataFrame: Normalized GRN dataframe.
        """
        df: pd.DataFrame = self._parse_tally_export(filepath)
        return df