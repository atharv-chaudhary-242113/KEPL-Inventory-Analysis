# src/processors/time_series_trainer.py
"""
Time-Series Training Processor module.
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
from sklearn.metrics import mean_absolute_percentage_error

logger = logging.getLogger(__name__)


class TimeSeriesTrainer:
    def __init__(self, min_months: int = 6) -> None:
        self.min_months: int = min_months

    def _extract_time_series(self, pv_df: pd.DataFrame, item: str, supplier: str) -> pd.DataFrame:
        mask = (pv_df['Item Details'] == item) & (pv_df['Particulars'] == supplier)
        df_subset = pv_df[mask].copy()

        if df_subset.empty:
            return pd.DataFrame()

        df_subset['month_year'] = df_subset['Date'].dt.to_period('M')
        ts = df_subset.groupby('month_year')['Qty.'].sum().reset_index()
        ts['month_year'] = ts['month_year'].dt.to_timestamp()
        ts = ts.sort_values('month_year').reset_index(drop=True)

        ts['time_idx'] = ts.index
        ts['month'] = ts['month_year'].dt.month
        ts['quarter'] = ts['month_year'].dt.quarter

        return ts

    def train_models(self, raw_pv_df: pd.DataFrame, models_dir: str | Path) -> dict[str, Any]:
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

            split_idx = int(len(ts_data) * 0.75)
            train_df, test_df = ts_data.iloc[:split_idx], ts_data.iloc[split_idx:]

            X_cols = ['time_idx', 'month', 'quarter']
            X_train, y_train = train_df[X_cols], train_df['Qty.']
            X_test, y_test = test_df[X_cols], test_df['Qty.']

            baseline_pred = np.full(shape=len(y_test), fill_value=y_train.mean())
            baseline_mape = mean_absolute_percentage_error(y_test, baseline_pred)

            model = xgb.XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
            model.fit(X_train, y_train)
            xgb_pred = model.predict(X_test)
            xgb_mape = mean_absolute_percentage_error(y_test, xgb_pred)

            if xgb_mape < baseline_mape:
                self._persist_model(model, target_dir, item, supplier, xgb_mape, baseline_mape)
                metrics['models_persisted'] += 1
            else:
                metrics['failed_validation'] += 1

            del model, train_df, test_df, ts_data
            if metrics['total_processed'] % 100 == 0:
                gc.collect()

        logger.info("Training cycle complete. Metrics: %s", metrics)
        return metrics

    def _persist_model(self, model: xgb.XGBRegressor, target_dir: Path, item: str, supplier: str, xgb_mape: float, baseline_mape: float) -> None:
        safe_item = "".join([c if c.isalnum() else "_" for c in item])
        safe_supplier = "".join([c if c.isalnum() else "_" for c in supplier])
        filename = f"xgb_{safe_item}_{safe_supplier}.joblib"

        final_path = target_dir / filename
        tmp_path = target_dir / f"{filename}.tmp"

        payload = {
            'model': model,
            'xgb_mape': float(xgb_mape),
            'baseline_mape': float(baseline_mape)
        }
        joblib.dump(payload, tmp_path)
        os.replace(tmp_path, final_path)