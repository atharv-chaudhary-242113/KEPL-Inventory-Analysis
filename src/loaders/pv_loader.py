# src/loaders/pv_loader.py
"""Purchase Vouchers (PV) dataset loader module."""

import pandas as pd

from .base_loader import BaseLoader


class PVLoader(BaseLoader):
    """
    Loader class responsible for processing final Purchase Vouchers.
    """

    def load(self, filepath: str) -> pd.DataFrame:
        """
        Load and normalize the PV dataset.

        Args:
            filepath (str): Path to the PV CSV file.

        Returns:
            pd.DataFrame: Normalized PV dataframe.
        """
        df: pd.DataFrame = self._parse_tally_export(filepath)
        return df