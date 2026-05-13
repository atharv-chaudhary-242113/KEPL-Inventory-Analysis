# src/analysis/simple_forecast.py
"""
Simple Forecasting Strategy module.

Executes unadjusted baseline forecasting logic parameterized by projected annual growth.
"""

import numpy as np
import pandas as pd

from .base_forecast_strategy import BaseForecastStrategy


class SimpleForecastStrategy(BaseForecastStrategy):
    """
    Computes reorder quantities derived solely from historical consumption averages,
    scaled by an expected annual growth projection.
    """

    def __init__(self, growth_rate: float = 1.30) -> None:
        """
        Initialize the forecast strategy.

        Args:
            growth_rate (float): Multiplier for annual demand projection. Default 1.30 (30% annual growth).
        """
        self.growth_rate: float = growth_rate

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Execute projected demand calculations.
        Applying the annual growth rate to the monthly average mathematically yields
        the projected monthly volume for the upcoming year.

        Args:
            aggregated_df (pd.DataFrame): Aggregated historical demand data.
            closing_stock_df (pd.DataFrame | None): Ignored in this strategy.

        Returns:
            pd.DataFrame: Dataframe with 'monthly_reorder_qty' and 'quarterly_reorder_qty'.
        """
        if aggregated_df.empty:
            return pd.DataFrame()

        df: pd.DataFrame = aggregated_df.copy()

        df['monthly_reorder_qty'] = np.ceil(df['avg_monthly_qty'] * self.growth_rate)
        df['quarterly_reorder_qty'] = np.ceil(df['avg_quarterly_qty'] * self.growth_rate)

        return df