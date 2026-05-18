# src/analysis/holt_winters_forecast.py
"""
Holt-Winters Triple Exponential Smoothing Forecasting Strategy module.
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd

from .base_forecast_strategy import BaseForecastStrategy
from .simple_forecast import SimpleForecastStrategy

logger = logging.getLogger(__name__)


class HoltWintersForecastStrategy(BaseForecastStrategy):
    """
    Computes reorder quantities using Holt-Winters Triple Exponential Smoothing.
    Adheres to the Open/Closed Principle for seamless integration into the forecasting execution pipeline.
    """

    def __init__(
            self,
            raw_pv_df: pd.DataFrame,
            seasonal_periods: int = 12,
            trend: str = 'add',
            seasonal: str = 'add',
            fallback_strategy=None,
            growth_rate: float = 1.30
    ) -> None:
        """
        Initialize the Holt-Winters forecasting strategy.

        Args:
            raw_pv_df (pd.DataFrame): Raw historical purchase voucher entries for time series extraction.
            seasonal_periods (int): Number of periods per seasonal cycle (e.g., 12 for monthly data).
            trend (str): Type of trend component ('add', 'mul', or None). Default 'add'.
            seasonal (str): Type of seasonal component ('add', 'mul', or None). Default 'add'.
            fallback_strategy (BaseForecastStrategy): Forecasting module utilized if data sparsity constraints fail.
            growth_rate (float): Multiplier for annual demand projection scale-up.
        """
        self.raw_pv_df: pd.DataFrame = raw_pv_df
        self.seasonal_periods: int = seasonal_periods
        self.trend: str = trend
        self.seasonal: str = seasonal
        self.fallback_strategy = fallback_strategy or SimpleForecastStrategy(growth_rate=growth_rate)
        self.growth_rate: float = growth_rate

    def _extract_time_series(self, item: str, supplier: str) -> pd.Series:
        """
        Extracts and aligns a continuous monthly time series for a distinct item-supplier pair.
        """
        mask = (self.raw_pv_df['Item Details'] == item) & (self.raw_pv_df['Particulars'] == supplier)
        df_subset = self.raw_pv_df[mask].copy()

        if df_subset.empty or 'Date' not in df_subset.columns:
            return pd.Series(dtype=float)

        df_subset['month_year'] = df_subset['Date'].dt.to_period('M')
        ts = df_subset.groupby('month_year')['Qty.'].sum()

        if ts.empty:
            return pd.Series(dtype=float)

        # Reindex to force explicit zero-filled continuity over the calendar sequence
        full_range = pd.period_range(start=ts.index.min(), end=ts.index.max(), freq='M')
        ts = ts.reindex(full_range, fill_value=0.0)
        return ts.to_timestamp()

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        if aggregated_df.empty:
            return pd.DataFrame()

        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
        except ImportError:
            logger.error("Dependency 'statsmodels' missing. Defaulting completely to structural baseline.")
            return self.fallback_strategy.compute(aggregated_df, closing_stock_df)

        df = self.fallback_strategy.compute(aggregated_df, closing_stock_df).copy()

        monthly_preds = []
        quarterly_preds = []
        algorithms = []
        mape_scores = []

        for _, row in df.iterrows():
            item = row['Item Details']
            supplier = row['Particulars']

            ts_data = self._extract_time_series(item, supplier)

            # Triple Smoothing structurally demands at least two complete seasonal cycles
            if len(ts_data) < 2 * self.seasonal_periods:
                monthly_preds.append(row['monthly_reorder_qty'])
                quarterly_preds.append(row['quarterly_reorder_qty'])
                algorithms.append("Baseline Average (Sparsity Fallback)")
                mape_scores.append("N/A")
                continue

            try:
                model = ExponentialSmoothing(
                    ts_data,
                    trend=self.trend,
                    seasonal=self.seasonal,
                    seasonal_periods=self.seasonal_periods,
                    initialization_method="estimated"
                )
                fitted_model = model.fit()

                # Project the upcoming rolling quarter (3 steps ahead)
                forecast = fitted_model.forecast(steps=3)
                pred_m1 = max(forecast.iloc[0], 0)
                pred_m2 = max(forecast.iloc[1], 0)
                pred_m3 = max(forecast.iloc[2], 0)

                # Compute Mean Absolute Percentage Error on in-sample fitted history
                in_sample_pred = fitted_model.fittedvalues
                valid_mask = ts_data > 0

                if valid_mask.sum() > 0:
                    mape = np.mean(np.abs(ts_data[valid_mask] - in_sample_pred[valid_mask]) / ts_data[valid_mask])
                    mape_score = round(float(mape) * 100, 2)
                else:
                    mape_score = 0.0

                monthly_preds.append(np.ceil(pred_m1 * self.growth_rate))
                quarterly_preds.append(np.ceil((pred_m1 + pred_m2 + pred_m3) * self.growth_rate))
                algorithms.append("Holt-Winters")
                mape_scores.append(mape_score)

            except Exception as e:
                logger.warning("Holt-Winters fitting failed for item '%s'. Reverting to baseline. Error: %s", item,
                               str(e))
                monthly_preds.append(row['monthly_reorder_qty'])
                quarterly_preds.append(row['quarterly_reorder_qty'])
                algorithms.append("Baseline Average (Fit Failure)")
                mape_scores.append("N/A")

        df['monthly_reorder_qty'] = monthly_preds
        df['quarterly_reorder_qty'] = quarterly_preds
        df['Forecast_Algorithm'] = algorithms
        df['Backtest_MAPE_%'] = mape_scores

        return df