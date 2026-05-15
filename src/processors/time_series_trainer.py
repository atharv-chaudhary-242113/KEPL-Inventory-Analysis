# src/processors/time_series_trainer.py
"""
Time-Series Training Processor module.

Isolates XGBoost training cycles from inference. Implements strict chronological
splitting, validation against deterministic baselines, and atomic persistence.
"""

import gc
import os
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

logger = logging.getLogger(__name__)


class TimeSeriesTrainer:
    """
    Executes training and validation of autoregressive models per procurement entity.
    Adheres to Single Responsibility Principle by decoupling model creation from inference.
    """

    def __init__(self, min_months: int = 6) -> None:
        """
        Initialize the trainer with data sparsity constraints.

        Args:
            min_months (int): Minimum sequential data points required to bypass 'Cold Start'.
        """
        self.min_months: int = min_months

    def _extract_time_series(self, pv_df: pd.DataFrame, item: str, supplier: str) -> pd.DataFrame:
        """Extract chronological monthly aggregation for a specific entity."""
        mask = (pv_df['Item Details'] == item) & (pv_df['Particulars'] == supplier)
        df_subset = pv_df[mask].copy()

        if df_subset.empty:
            return pd.DataFrame()

        df_subset['month_year'] = df_subset['Date'].dt.to_period('M')
        ts = df_subset.groupby('month_year')['Qty.'].sum().reset_index()
        ts['month_year'] = ts['month_year'].dt.to_timestamp()
        ts = ts.sort_values('month_year').reset_index(drop=True)

        # Feature Engineering
        ts['time_idx'] = ts.index
        ts['month'] = ts['month_year'].dt.month
        ts['quarter'] = ts['month_year'].dt.quarter

        return ts

    def train_models(self, raw_pv_df: pd.DataFrame, models_dir: str | Path) -> dict[str, Any]:
        """
        Execute the training loop, evaluating XGBoost against the simple average.

        Args:
            raw_pv_df (pd.DataFrame): The unaggregated, chronological purchase voucher dataset.
            models_dir (str | Path): Target directory for atomic joblib persistence.

        Returns:
            dict: Execution metrics including total trained, skipped, and superior models.
        """
        target_dir = Path(models_dir)
        os.makedirs(target_dir, exist_ok=True)

        metrics = {'total_processed': 0, 'skipped_sparsity': 0, 'models_persisted': 0, 'failed_validation': 0}

        if raw_pv_df.empty or 'Date' not in raw_pv_df.columns:
            logger.error("Raw PV dataset is invalid for time-series training.")
            return metrics

        unique_entities = raw_pv_df[['Item Details', 'Particulars']].drop_duplicates()

        for _, row in unique_entities.iterrows():
            item = row['Item Details']
            supplier = row['Particulars']

            ts_data = self._extract_time_series(raw_pv_df, item, supplier)
            metrics['total_processed'] += 1

            if len(ts_data) < self.min_months:
                metrics['skipped_sparsity'] += 1
                continue

            # Chronological Split (75/25)
            split_idx = int(len(ts_data) * 0.75)
            train_df, test_df = ts_data.iloc[:split_idx], ts_data.iloc[split_idx:]

            X_cols = ['time_idx', 'month', 'quarter']
            X_train, y_train = train_df[X_cols], train_df['Qty.']
            X_test, y_test = test_df[X_cols], test_df['Qty.']

            # Baseline: Simple Average of Training Data
            baseline_pred = np.full(shape=len(y_test), fill_value=y_train.mean())
            baseline_mae = mean_absolute_error(y_test, baseline_pred)

            # XGBoost Execution
            model = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
            model.fit(X_train, y_train)
            xgb_pred = model.predict(X_test)
            xgb_mae = mean_absolute_error(y_test, xgb_pred)

            # Validation Protocol
            if xgb_mae < baseline_mae:
                self._persist_model(model, target_dir, item, supplier)
                metrics['models_persisted'] += 1
            else:
                metrics['failed_validation'] += 1

            # Memory Management
            del model, train_df, test_df, ts_data
            if metrics['total_processed'] % 100 == 0:
                gc.collect()

        logger.info("Training cycle complete. Metrics: %s", metrics)
        return metrics

    def _persist_model(self, model: xgb.XGBRegressor, target_dir: Path, item: str, supplier: str) -> None:
        """Atomic persistence to prevent I/O race conditions."""
        safe_item = "".join([c if c.isalnum() else "_" for c in item])
        safe_supplier = "".join([c if c.isalnum() else "_" for c in supplier])
        filename = f"xgb_{safe_item}_{safe_supplier}.joblib"

        final_path = target_dir / filename
        tmp_path = target_dir / f"{filename}.tmp"

        joblib.dump(model, tmp_path)
        os.replace(tmp_path, final_path)