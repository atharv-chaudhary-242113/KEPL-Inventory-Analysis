# src/analysis/anomaly_detector.py
"""
Procurement Anomaly Detection module.

Applies unsupervised Isolation Forest clustering to evaluate cross-sectional
procurement entries and flag operational anomalies based on multivariate distribution characteristics.
"""

import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Executes structural transaction scoring on purchase voucher logs.
    Isolates statistical anomalies across volumetric, pricing, and temporal indices.
    """

    def __init__(self, contamination: str | float = 'auto', random_state: int = 42) -> None:
        """
        Initialize anomaly configuration parameters.

        Args:
            contamination (str | float): Expected ratio of outliers within data grid.
            random_state (int): Enforces deterministic execution bounds across cycles.
        """
        self.contamination = contamination
        self.random_state = random_state

    def detect(self, pv_df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates the transaction matrix for variance divergence.

        Args:
            pv_df (pd.DataFrame): Validated, cleaned transaction DataFrame.

        Returns:
            pd.DataFrame: Subset containing identified anomalies accompanied by scoring metrics.
        """
        if pv_df.empty or not {'Price', 'Qty.', 'Date'}.issubset(pv_df.columns):
            logger.warning("Data schema criteria unmet. Inception of anomaly evaluation aborted.")
            return pd.DataFrame()

        # Construct isolation feature space mapping to prevent target multicollinearity
        features = pd.DataFrame()
        features['unit_price'] = pv_df['Price'].fillna(0.0)
        features['qty'] = pv_df['Qty.'].fillna(0.0)
        features['month_of_year'] = pv_df['Date'].dt.month.fillna(1)

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )

        preds = model.fit_predict(features)
        scores = model.decision_function(features)

        evaluated_df = pv_df.copy()
        evaluated_df['anomaly_score'] = scores
        evaluated_df['is_anomaly'] = preds == -1

        anomalies_df = evaluated_df[evaluated_df['is_anomaly']].copy()

        if not anomalies_df.empty:
            logger.warning(
                "Execution anomaly detection complete. Identified %d outlying observations.",
                len(anomalies_df)
            )
            for _, row in anomalies_df.iterrows():
                logger.warning(
                    "Anomaly signature: Item='%s', Vendor='%s', Qty=%s, Price=%s | Score=%.4f",
                    row.get('Item Details', 'unknown'),
                    row.get('Particulars', 'unknown'),
                    row.get('Qty.', 0),
                    row.get('Price', 0),
                    row.get('anomaly_score', 0.0)
                )

        return anomalies_df