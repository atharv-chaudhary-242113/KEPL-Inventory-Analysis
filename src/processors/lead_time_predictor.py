# src/processors/lead_time_predictor.py
"""
Lead Time Predictor module.

Applies machine learning to predict dynamic lead timelines, employing model persistence
and rigorous performance baseline validations.
"""

import os
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OrdinalEncoder

logger = logging.getLogger(__name__)


class LeadTimePredictor:
    """
    Random Forest based predictor for estimating operational supply delays.
    Maintains OCP constraints via automated fallback to empirical baselines.
    """

    def __init__(self) -> None:
        """Initialize the model state and persistence pathways."""
        self.model_path: Path = Path(__file__).resolve().parent.parent.parent / 'models' / 'lead_time_predictor.joblib'
        self.model: RandomForestRegressor | None = None
        self.encoder: OrdinalEncoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
        self.is_trained: bool = False
        self.empirical_fallback: pd.DataFrame = pd.DataFrame()

    def train_or_load(self, linked_df: pd.DataFrame, empirical_stats: pd.DataFrame) -> None:
        """
        Execute model acquisition, evaluation, and conditional persistence.

        Args:
            linked_df (pd.DataFrame): Validated historical timeline data.
            empirical_stats (pd.DataFrame): Aggregated statistical baseline averages.
        """
        self.empirical_fallback = empirical_stats.copy()

        if self.model_path.exists():
            try:
                payload = joblib.load(self.model_path)
                self.model = payload['model']
                self.encoder = payload['encoder']
                self.is_trained = True
                logger.info("Loaded persisted model from disk.")
                return
            except Exception as e:
                logger.error("Failed to load model from disk: %s", e)

        if len(linked_df) < 30:
            logger.warning("Insufficient samples (<30) for training. Falling back to empirical average.")
            return

        df_train = linked_df.copy()
        df_train['month_of_year'] = df_train['POV_Date'].dt.month

        X_raw = df_train[['Item Details', 'Particulars']]
        encoded = self.encoder.fit_transform(X_raw)

        X = pd.DataFrame(encoded, columns=['item_encoded', 'supplier_encoded'])
        X['order_qty'] = df_train['POV_Qty'].values
        X['month_of_year'] = df_train['month_of_year'].values
        y = df_train['lead_time_days'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        candidate_model = RandomForestRegressor(random_state=42, n_estimators=100)
        candidate_model.fit(X_train, y_train)

        rf_preds = candidate_model.predict(X_test)
        rf_mae: float = mean_absolute_error(y_test, rf_preds)

        baseline_preds = []
        for i in X_test.index:
            item_idx = X_test.loc[i, 'item_encoded']
            supp_idx = X_test.loc[i, 'supplier_encoded']
            try:
                raw_item = self.encoder.categories_[0][int(item_idx)]
                raw_supp = self.encoder.categories_[1][int(supp_idx)]
                mask = (self.empirical_fallback['Item Details'] == raw_item) & \
                       (self.empirical_fallback['Particulars'] == raw_supp)
                if mask.any():
                    baseline_preds.append(self.empirical_fallback.loc[mask, 'avg_lead_time_days'].values[0])
                else:
                    baseline_preds.append(y_train.mean())
            except Exception:
                baseline_preds.append(y_train.mean())

        baseline_mae: float = mean_absolute_error(y_test, baseline_preds)

        if rf_mae >= baseline_mae:
            logger.warning("Model MAE (%.2f days) not better than baseline (%.2f days). Falling back.", rf_mae,
                           baseline_mae)
            return

        self.model = candidate_model
        self.is_trained = True

        os.makedirs(self.model_path.parent, exist_ok=True)
        joblib.dump({'model': self.model, 'encoder': self.encoder}, self.model_path)
        logger.info("Model trained and persisted. RF MAE: %.2f vs Baseline MAE: %.2f", rf_mae, baseline_mae)

    def predict(self, item: str, supplier: str, qty: float, month: int) -> float:
        """
        Execute prediction protocol, reverting to deterministic baselines if model unavailable.

        Args:
            item (str): Material Identity.
            supplier (str): Source Identity.
            qty (float): Order magnitude.
            month (int): Calendar period component.

        Returns:
            float: Predicted lead time span in days.
        """
        if not self.is_trained or self.model is None:
            mask = (self.empirical_fallback['Item Details'] == item) & \
                   (self.empirical_fallback['Particulars'] == supplier)
            if mask.any():
                return float(self.empirical_fallback.loc[mask, 'avg_lead_time_days'].values[0])
            return 0.0

        encoded = self.encoder.transform([[item, supplier]])
        X_pred = pd.DataFrame({
            'item_encoded': [encoded[0][0]],
            'supplier_encoded': [encoded[0][1]],
            'order_qty': [qty],
            'month_of_year': [month]
        })

        pred = self.model.predict(X_pred)
        return float(pred[0])