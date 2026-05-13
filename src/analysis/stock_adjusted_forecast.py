# src/analysis/stock_adjusted_forecast.py
"""
Stock-Adjusted Forecasting Strategy module.

Future extension point for net demand calculation.
"""

import pandas as pd

from .base_forecast_strategy import BaseForecastStrategy


class StockAdjustedForecastStrategy(BaseForecastStrategy):
    """
    Computes net demand by subtracting existing closing stock from gross demand estimates.
    Maintains the Open/Closed Principle structural stub pending dataset availability.
    """

    def __init__(self, growth_rate: float = 1.30) -> None:
        """
        Initialize the forecast strategy.

        Args:
            growth_rate (float): Multiplier for annual demand projection.
        """
        self.growth_rate: float = growth_rate

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Execute net demand calculations.

        Args:
            aggregated_df (pd.DataFrame): Aggregated historical demand data.
            closing_stock_df (pd.DataFrame | None): Current period stock level data.

        Raises:
            NotImplementedError: Standard structural enforcement prior to dataset delivery.
        """
        raise NotImplementedError(
            "StockAdjustedForecastStrategy requires closing stock data implementation. "
            "System will auto-fallback to SimpleForecastStrategy."
        )