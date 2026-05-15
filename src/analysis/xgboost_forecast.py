# src/analysis/xgboost_forecast.py
"""
XGBoost Forecasting Strategy module.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from .base_forecast_strategy import BaseForecastStrategy
from .simple_forecast import SimpleForecastStrategy

logger = logging.getLogger(__name__)


class XGBoostForecastStrategy(BaseForecastStrategy):
    def __init__(self, models_dir: str | Path, fallback_strategy=None, growth_rate: float = 1.30) -> None:
        self.models_dir: Path = Path(models_dir)
        self.fallback_strategy = fallback_strategy or SimpleForecastStrategy(growth_rate=growth_rate)
        self.growth_rate: float = growth_rate

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        if aggregated_df.empty:
            return pd.DataFrame()

        df = self.fallback_strategy.compute(aggregated_df, closing_stock_df).copy()

        monthly_preds = []
        quarterly_preds = []
        algorithms = []
        mape_scores = []

        for _, row in df.iterrows():
            item = row['Item Details']
            supplier = row['Particulars']
            months_covered = row.get('months_covered', 12)

            safe_item = "".join([c if c.isalnum() else "_" for c in item])
            safe_supplier = "".join([c if c.isalnum() else "_" for c in supplier])
            model_path = self.models_dir / f"xgb_{safe_item}_{safe_supplier}.joblib"

            if model_path.exists():
                try:
                    payload = joblib.load(model_path)

                    model = payload['model'] if isinstance(payload, dict) and 'model' in payload else payload
                    xgb_mape = round(payload['xgb_mape'] * 100, 2) if isinstance(payload,
                                                                                 dict) and 'xgb_mape' in payload else "Verified (Legacy)"

                    base_idx = months_covered

                    X_pred_m1 = pd.DataFrame({'time_idx': [base_idx], 'month': [(base_idx % 12) + 1],
                                              'quarter': [((base_idx // 3) % 4) + 1]})
                    X_pred_m2 = pd.DataFrame({'time_idx': [base_idx + 1], 'month': [((base_idx + 1) % 12) + 1],
                                              'quarter': [(((base_idx + 1) // 3) % 4) + 1]})
                    X_pred_m3 = pd.DataFrame({'time_idx': [base_idx + 2], 'month': [((base_idx + 2) % 12) + 1],
                                              'quarter': [(((base_idx + 2) // 3) % 4) + 1]})

                    pred_m1 = model.predict(X_pred_m1)[0]
                    pred_m2 = model.predict(X_pred_m2)[0]
                    pred_m3 = model.predict(X_pred_m3)[0]

                    monthly_preds.append(np.ceil(max(pred_m1, 0) * self.growth_rate))
                    quarterly_preds.append(np.ceil(max(pred_m1 + pred_m2 + pred_m3, 0) * self.growth_rate))
                    algorithms.append("XGBoost")
                    mape_scores.append(xgb_mape)
                    continue

                except Exception as e:
                    logger.warning("Failed to run inference for %s. Reverting to baseline. Error: %s", item, e)

            # Fallback block
            monthly_preds.append(row['monthly_reorder_qty'])
            quarterly_preds.append(row['quarterly_reorder_qty'])
            algorithms.append("Baseline Average")
            mape_scores.append("N/A")

        df['monthly_reorder_qty'] = monthly_preds
        df['quarterly_reorder_qty'] = quarterly_preds
        df['Forecast_Algorithm'] = algorithms
        df['Backtest_MAPE_%'] = mape_scores

        return df