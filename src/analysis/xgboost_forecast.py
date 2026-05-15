# src/analysis/xgboost_forecast.py
"""
XGBoost Forecasting Strategy module.

Executes inference using persisted ML models. Strictly adheres to OCP by extending
BaseForecastStrategy and falling back to SimpleForecastStrategy when models are absent.
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
    """
    ML-driven inference engine. Predicts t+1 and t+3 quantities utilizing pre-trained,
    validated XGBoost regressors stored on disk.
    """

    def __init__(self, models_dir: str | Path, growth_rate: float = 1.30) -> None:
        """
        Initialize inference engine.

        Args:
            models_dir (str | Path): Location of persisted .joblib models.
            growth_rate (float): Base growth rate used for baseline fallback.
        """
        self.models_dir: Path = Path(models_dir)
        self.fallback_strategy = SimpleForecastStrategy(growth_rate=growth_rate)
        self.growth_rate: float = growth_rate

    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Execute dynamic predictions. Reverts to SimpleForecastStrategy per item if ML model is unavailable.

        Args:
            aggregated_df (pd.DataFrame): Aggregated historical demand data.
            closing_stock_df (pd.DataFrame | None): Stock level data (Future).

        Returns:
            pd.DataFrame: DataFrame containing monthly and quarterly reorder quantities.
        """
        if aggregated_df.empty:
            return pd.DataFrame()

        # Compute baselines for fallback
        baseline_df = self.fallback_strategy.compute(aggregated_df, closing_stock_df)
        df = baseline_df.copy()

        monthly_preds = []
        quarterly_preds = []

        for _, row in df.iterrows():
            item = row['Item Details']
            supplier = row['Particulars']
            months_covered = row.get('months_covered', 12)

            safe_item = "".join([c if c.isalnum() else "_" for c in item])
            safe_supplier = "".join([c if c.isalnum() else "_" for c in supplier])
            model_path = self.models_dir / f"xgb_{safe_item}_{safe_supplier}.joblib"

            if model_path.exists():
                try:
                    model = joblib.load(model_path)

                    # Construct inference feature vector for t+1 to t+3
                    # Approximating next temporal indices
                    base_idx = months_covered

                    # Month 1 prediction (Monthly Reorder)
                    X_pred_m1 = pd.DataFrame({
                        'time_idx': [base_idx],
                        'month': [(base_idx % 12) + 1],
                        'quarter': [((base_idx // 3) % 4) + 1]
                    })
                    pred_m1 = model.predict(X_pred_m1)[0]

                    # Month 2 and 3 predictions (For Quarterly Reorder)
                    X_pred_m2 = pd.DataFrame({'time_idx': [base_idx + 1], 'month': [((base_idx + 1) % 12) + 1],
                                              'quarter': [(((base_idx + 1) // 3) % 4) + 1]})
                    X_pred_m3 = pd.DataFrame({'time_idx': [base_idx + 2], 'month': [((base_idx + 2) % 12) + 1],
                                              'quarter': [(((base_idx + 2) // 3) % 4) + 1]})

                    pred_m2 = model.predict(X_pred_m2)[0]
                    pred_m3 = model.predict(X_pred_m3)[0]

                    monthly_reorder = np.ceil(max(pred_m1, 0) * self.growth_rate)
                    quarterly_reorder = np.ceil(max(pred_m1 + pred_m2 + pred_m3, 0) * self.growth_rate)

                    monthly_preds.append(monthly_reorder)
                    quarterly_preds.append(quarterly_reorder)
                except Exception as e:
                    logger.warning("Failed to run inference for %s. Reverting to baseline. Error: %s", item, e)
                    monthly_preds.append(row['monthly_reorder_qty'])
                    quarterly_preds.append(row['quarterly_reorder_qty'])
            else:
                monthly_preds.append(row['monthly_reorder_qty'])
                quarterly_preds.append(row['quarterly_reorder_qty'])

        df['monthly_reorder_qty'] = monthly_preds
        df['quarterly_reorder_qty'] = quarterly_preds

        return df