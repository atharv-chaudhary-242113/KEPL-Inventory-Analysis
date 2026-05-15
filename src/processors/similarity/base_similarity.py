# src/processors/similarity/base_similarity.py
"""
Base Similarity Strategy interface.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseSimilarityStrategy(ABC):
    """
    Abstract contract for duplicate entity detection algorithms.
    """

    @abstractmethod
    def flag_similar(self, df: pd.DataFrame, column: str, threshold: float) -> None:
        """
        Identify and log potentially duplicated entities within a target column.

        Args:
            df (pd.DataFrame): Target dataframe.
            column (str): Target column nomenclature.
            threshold (float): Minimum confidence threshold to trigger a flag.
        """
        pass