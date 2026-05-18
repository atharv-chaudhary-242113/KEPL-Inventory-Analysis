# src/analysis/ensemble_forecast.py
import pandas as pd
import numpy as np
from .base_forecast_strategy import BaseForecastStrategy


class DynamicEnsembleForecastStrategy(BaseForecastStrategy):
    """
    Executes MAPE-driven dynamic algorithm selection to eliminate overfitting.
    """

    def __init__(self, xgb_strategy, hw_strategy, fallback_strategy) -> None:
        self.xgb_strategy = xgb_strategy
        self.hw_strategy = hw_strategy
        self.fallback_strategy = fallback_strategy

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        if aggregated_df.empty:
            return pd.DataFrame()

        # Generate independent predictions
        xgb_df = self.xgb_strategy.compute(aggregated_df, closing_stock_df)
        hw_df = self.hw_strategy.compute(aggregated_df, closing_stock_df)
        base_df = self.fallback_strategy.compute(aggregated_df, closing_stock_df)

        final_df = base_df.copy()

        for idx in final_df.index:
            xgb_mape = xgb_df.at[idx, 'Backtest_MAPE_%']
            hw_mape = hw_df.at[idx, 'Backtest_MAPE_%']

            xgb_valid = isinstance(xgb_mape, (int, float))
            hw_valid = isinstance(hw_mape, (int, float))

            # Selection Logic
            if xgb_valid and hw_valid:
                winner = xgb_df if xgb_mape <= hw_mape else hw_df
            elif xgb_valid:
                winner = xgb_df
            elif hw_valid:
                winner = hw_df
            else:
                winner = base_df

            final_df.at[idx, 'monthly_reorder_qty'] = winner.at[idx, 'monthly_reorder_qty']
            final_df.at[idx, 'quarterly_reorder_qty'] = winner.at[idx, 'quarterly_reorder_qty']

            algo_name = winner.at[
                idx, 'Forecast_Algorithm'] if 'Forecast_Algorithm' in winner.columns else 'Baseline Average'
            mape_val = winner.at[idx, 'Backtest_MAPE_%'] if 'Backtest_MAPE_%' in winner.columns else 'N/A'

            final_df.at[idx, 'Forecast_Algorithm'] = f"Ensemble: {algo_name}"
            final_df.at[idx, 'Backtest_MAPE_%'] = mape_val

        return final_df