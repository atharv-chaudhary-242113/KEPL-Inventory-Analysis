# src/analysis/anomaly_detector.py
"""
Anomaly Detection module.

Isolates irregular procurement events using unsupervised learning.
"""

import logging
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects procurement anomalies based on multidimensional feature space (price, quantity, timing).
    Amount is excluded to prevent multicollinearity bias.
    """

    def __init__(self, contamination: str | float = 'auto', random_state: int = 42) -> None:
        """
        Initialize the Isolation Forest detector.

        Args:
            contamination (str | float): Expected proportion of outliers in the data.
            random_state (int): Seed for deterministic execution.
        """
        self.contamination: str | float = contamination
        self.random_state: int = random_state

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify anomalous rows in the procurement dataset.

        Args:
            df (pd.DataFrame): Cleaned procurement transactional dataframe.

        Returns:
            pd.DataFrame: Dataframe appended with 'is_anomaly' (bool) and 'anomaly_score' (float).
        """
        if df.empty:
            return df

        required_cols: list[str] = ['Price', 'Qty.', 'Date']
        if not all(c in df.columns for c in required_cols):
            return df

        analysis_df: pd.DataFrame = df.copy()
        analysis_df['month_of_year'] = analysis_df['Date'].dt.month

        valid_mask: pd.Series = analysis_df['Price'].notna() & analysis_df['Qty.'].notna() & analysis_df[
            'month_of_year'].notna()
        if not valid_mask.any():
            analysis_df['is_anomaly'] = False
            analysis_df['anomaly_score'] = 0.0
            return analysis_df

        X: pd.DataFrame = analysis_df.loc[valid_mask, ['Price', 'Qty.', 'month_of_year']]

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state
        )
        model.fit(X)

        analysis_df.loc[valid_mask, 'is_anomaly'] = model.predict(X) == -1
        analysis_df.loc[valid_mask, 'anomaly_score'] = model.decision_function(X)

        analysis_df['is_anomaly'] = analysis_df['is_anomaly'].fillna(False).astype(bool)
        analysis_df['anomaly_score'] = analysis_df['anomaly_score'].fillna(0.0)

        anomalies_count: int = int(analysis_df['is_anomaly'].sum())
        if anomalies_count > 0:
            logger.warning("%d anomalous procurement record(s) flagged. See Anomaly Report sheet.", anomalies_count)

        return analysis_df.drop(columns=['month_of_year'])