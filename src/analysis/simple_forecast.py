# src/analysis/simple_forecast.py
import pandas as pd
import numpy as np
from .base_forecast_strategy import BaseForecastStrategy

class SimpleForecastStrategy(BaseForecastStrategy):
    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame = None) -> pd.DataFrame:
        df = aggregated_df.copy()
        df['monthly_reorder_qty'] = np.ceil(df['avg_monthly_qty'])
        df['quarterly_reorder_qty'] = np.ceil(df['avg_quarterly_qty'])
        return df