# src/analysis/base_forecast_strategy.py
"""
Abstract forecast strategy module.

Defines the contract for demand forecasting algorithms.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseForecastStrategy(ABC):
    """
    Abstract base class defining the contract for demand forecasting strategies.
    Complies with the Open/Closed Principle to allow future algorithm extensions.
    """

    @abstractmethod
    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Compute reorder quantities.

        Args:
            aggregated_df (pd.DataFrame): Aggregated historical demand data.
            closing_stock_df (pd.DataFrame | None): Optional stock level data. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame containing computed forecast quantities.
        """
        pass