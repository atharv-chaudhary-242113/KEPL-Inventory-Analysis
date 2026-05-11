# src/analysis/stock_adjusted_forecast.py
import pandas as pd
import numpy as np
from .base_forecast_strategy import BaseForecastStrategy


class StockAdjustedForecastStrategy(BaseForecastStrategy):
    """
    Forecast strategy utilizing closing stock data.
    Demonstrates Open/Closed Principle (OCP) by extending BaseForecastStrategy
    without modifying existing SimpleForecastStrategy.
    """

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Calculates reorder quantities adjusted for current closing stock.

        Args:
            aggregated_df (pd.DataFrame): Demand aggregated data.
            closing_stock_df (pd.DataFrame): Processed closing stock data.

        Returns:
            pd.DataFrame: Forecast dataframe with net demand requirements.

        Raises:
            ValueError: If closing_stock_df is not provided.
        """
        if closing_stock_df is None or closing_stock_df.empty:
            raise ValueError("StockAdjustedForecastStrategy requires valid closing_stock_df.")

        df = aggregated_df.copy()

        # Merge demand with closing stock on Item Details
        # Assuming closing_stock_df has columns: 'Item Details', 'Closing Qty'
        df = pd.merge(df, closing_stock_df[['Item Details', 'Closing Qty']], on='Item Details', how='left')
        df['Closing Qty'] = df['Closing Qty'].fillna(0)

        # Net demand calculation: Gross demand minus available stock
        df['net_monthly_demand'] = df['avg_monthly_qty'] - df['Closing Qty']
        df['net_monthly_demand'] = np.where(df['net_monthly_demand'] < 0, 0, df['net_monthly_demand'])

        df['monthly_reorder_qty'] = np.ceil(df['net_monthly_demand'])
        df['quarterly_reorder_qty'] = np.ceil(df['net_monthly_demand'] * 3)

        return df