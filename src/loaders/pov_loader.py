# src/loaders/pov_loader.py
"""Purchase Order Vouchers (POV) dataset loader module."""

import pandas as pd

from .base_loader import BaseLoader


class POVLoader(BaseLoader):
    """
    Loader class responsible for processing Purchase Order Vouchers.
    """

    def load(self, filepath: str) -> pd.DataFrame:
        """
        Load and normalize the POV dataset.

        Args:
            filepath (str): Path to the POV CSV file.

        Returns:
            pd.DataFrame: Normalized POV dataframe.
        """
        df: pd.DataFrame = self._parse_tally_export(filepath)
        return df