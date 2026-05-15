# src/processors/data_cleaner.py
"""
Data Cleaner module.

Provides stateless utilities for data normalization, cleaning,
and output sanitization. Delegates similarity detection via Strategy Pattern.
"""

import logging
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.processors.similarity.base_similarity import BaseSimilarityStrategy

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Stateless utility class for executing core data cleaning protocols.
    """

    @staticmethod
    def forward_fill_voucher_fields(df: pd.DataFrame) -> pd.DataFrame:
        fill_cols: list[str] = ['Date', 'Vch/Bill No', 'Particulars']
        available: list[str] = [c for c in fill_cols if c in df.columns]
        if available:
            df[available] = df[available].ffill()
        return df

    @staticmethod
    def cast_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        cols: list[str] = ['Qty.', 'Price', 'Amount']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        return df

    @staticmethod
    def drop_non_item_rows(df: pd.DataFrame) -> pd.DataFrame:
        initial_count: int = len(df)
        if 'Unit' in df.columns:
            df = df[df['Unit'] != '-']
        if 'Item Details' in df.columns:
            pattern: str = 'freight|tax|charge'
            mask: pd.Series = df['Item Details'].astype(str).str.lower().str.contains(pattern, na=False)
            df = df[~mask]

        dropped: int = initial_count - len(df)
        if dropped > 0:
            logger.warning("%d rows dropped (freight/tax entries)", dropped)
        return df

    @staticmethod
    def normalise_item_names(df: pd.DataFrame) -> pd.DataFrame:
        cols: list[str] = ['Item Details', 'Particulars']
        for c in cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.lower()
        return df

    @staticmethod
    def flag_similar_entities(df: pd.DataFrame, column: str, strategy: 'BaseSimilarityStrategy', threshold: float = 0.85) -> None:
        """
        Delegate duplicate flagging to the injected algorithm strategy.
        """
        strategy.flag_similar(df, column, threshold)

    @staticmethod
    def sanitise_for_export(df: pd.DataFrame) -> pd.DataFrame:
        clean_df: pd.DataFrame = df.copy()
        str_cols: pd.Index = clean_df.select_dtypes(include=['object', 'string']).columns

        injection_chars: tuple[str, ...] = ('=', '+', '-', '@')

        for col in str_cols:
            mask: pd.Series = clean_df[col].astype(str).str.startswith(injection_chars, na=False)
            clean_df.loc[mask, col] = "'" + clean_df.loc[mask, col].astype(str)

        return clean_df