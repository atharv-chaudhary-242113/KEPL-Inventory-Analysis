# src/loaders/tally_loader.py
import pandas as pd
import logging
from .base_loader import BaseLoader
from ..processors.data_cleaner import DataCleaner

logger = logging.getLogger("kepl_pipeline")


class TallyCSVLoader(BaseLoader):
    """Base class for GRN, POV, and PV loaders to maintain DRY."""

    def load(self, filepath: str) -> pd.DataFrame:
        logger.debug(f"Loading file: {filepath}")
        try:
            df = pd.read_csv(filepath, skiprows=5)
            # Ensure row 0 becomes headers if pandas didn't infer correctly due to skips
            if df.columns[0] == "Unnamed: 0" or "Date" not in df.columns:
                df.columns = df.iloc[0]
                df = df[1:].reset_index(drop=True)

            df = DataCleaner.forward_fill_voucher_fields(df)
            df = DataCleaner.cast_numeric_columns(df)
            df = DataCleaner.drop_non_item_rows(df)
            df = DataCleaner.normalise_item_names(df)

            logger.info(f"Loaded {len(df)} rows from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {str(e)}")
            raise


class GRNLoader(TallyCSVLoader):
    pass


class POVLoader(TallyCSVLoader):
    pass


class PVLoader(TallyCSVLoader):
    pass


class ClosingStockLoader(BaseLoader):
    def load(self, filepath: str) -> pd.DataFrame:
        if not filepath:
            return None
        # Stub for future implementation
        raise NotImplementedError("ClosingStockLoader not yet implemented.")