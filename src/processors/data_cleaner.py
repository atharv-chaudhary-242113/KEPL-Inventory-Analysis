# src/processors/data_cleaner.py
"""
Data Cleaner module.

Provides stateless utilities for data normalization, cleaning,
duplicate detection, and output sanitization.
"""

import logging
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Stateless utility class for executing core data cleaning and normalisation protocols.
    """

    @staticmethod
    def forward_fill_voucher_fields(df: pd.DataFrame) -> pd.DataFrame:
        """
        Forward-fill structural voucher metadata.

        Args:
            df (pd.DataFrame): Raw parsed DataFrame.

        Returns:
            pd.DataFrame: DataFrame with populated identity columns.
        """
        fill_cols: list[str] = ['Date', 'Vch/Bill No', 'Particulars']
        available: list[str] = [c for c in fill_cols if c in df.columns]
        if available:
            df[available] = df[available].ffill()
        return df

    @staticmethod
    def cast_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Force-cast transactional value columns to float representations.

        Args:
            df (pd.DataFrame): DataFrame containing raw numeric strings.

        Returns:
            pd.DataFrame: DataFrame with float types applied to computational fields.
        """
        cols: list[str] = ['Qty.', 'Price', 'Amount']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        return df

    @staticmethod
    def drop_non_item_rows(df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter auxiliary rows that do not constitute physical inventory objects.

        Args:
            df (pd.DataFrame): DataFrame containing mixed ledger entries.

        Returns:
            pd.DataFrame: DataFrame containing only material items.
        """
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
        """
        Standardize string identities for deduplication and grouping operations.

        Args:
            df (pd.DataFrame): Target DataFrame.

        Returns:
            pd.DataFrame: DataFrame with normalized string identity targets.
        """
        cols: list[str] = ['Item Details', 'Particulars']
        for c in cols:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip().str.lower()
        return df

    @staticmethod
    def _flag_similar_entities(df: pd.DataFrame, column: str, threshold: float) -> None:
        """
        Internal implementation for TF-IDF based string similarity scoring.

        Args:
            df (pd.DataFrame): Target DataFrame.
            column (str): Target column to analyze.
            threshold (float): Minimum cosine similarity score.

        Raises:
            ValueError: If threshold is outside domain [0.5, 1.0].
        """
        if not (0.5 <= threshold <= 1.0):
            raise ValueError(f"Threshold {threshold} invalid. Must be within [0.5, 1.0].")

        if column not in df.columns or df.empty:
            return

        unique_entities: np.ndarray = df[column].dropna().unique()
        if len(unique_entities) < 2:
            return

        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        tfidf_matrix = vectorizer.fit_transform(unique_entities)
        sim_matrix: np.ndarray = cosine_similarity(tfidf_matrix)

        np.fill_diagonal(sim_matrix, 0)
        indices = np.where(sim_matrix >= threshold)

        flagged: set[tuple[str, str]] = set()
        for i, j in zip(indices[0], indices[1]):
            if i < j:
                e1, e2 = unique_entities[i], unique_entities[j]
                pair = tuple(sorted([e1, e2]))
                if pair not in flagged:
                    flagged.add(pair)
                    logger.warning(
                        "Similar %s detected: '%s' vs '%s' [score: %.3f]",
                        column, e1, e2, sim_matrix[i, j]
                    )

    @staticmethod
    def flag_similar_item_names(df: pd.DataFrame, threshold: float = 0.85) -> None:
        """
        Log warnings for potentially duplicated item nomenclatures using TF-IDF.

        Args:
            df (pd.DataFrame): DataFrame containing 'Item Details'.
            threshold (float): Minimum similarity to trigger warning (0.5 - 1.0).
        """
        DataCleaner._flag_similar_entities(df, 'Item Details', threshold)

    @staticmethod
    def flag_similar_supplier_names(df: pd.DataFrame, threshold: float = 0.85) -> None:
        """
        Log warnings for potentially duplicated supplier nomenclatures using TF-IDF.

        Args:
            df (pd.DataFrame): DataFrame containing 'Particulars'.
            threshold (float): Minimum similarity to trigger warning (0.5 - 1.0).
        """
        DataCleaner._flag_similar_entities(df, 'Particulars', threshold)

    @staticmethod
    def sanitise_for_export(df: pd.DataFrame) -> pd.DataFrame:
        """
        Prevent payload execution in downstream spreadsheet processors via injection sanitization.

        Args:
            df (pd.DataFrame): Source DataFrame.

        Returns:
            pd.DataFrame: A sanitized copy of the DataFrame.
        """
        clean_df: pd.DataFrame = df.copy()
        str_cols: pd.Index = clean_df.select_dtypes(include=['object', 'string']).columns

        injection_chars: tuple[str, ...] = ('=', '+', '-', '@')

        for col in str_cols:
            mask: pd.Series = clean_df[col].astype(str).str.startswith(injection_chars, na=False)
            clean_df.loc[mask, col] = "'" + clean_df.loc[mask, col].astype(str)

        return clean_df