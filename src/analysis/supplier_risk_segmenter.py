# src/analysis/supplier_risk_segmenter.py
"""
Supplier Risk Segmenter module.

Applies K-Means clustering to multidimensional vendor performance vectors
to isolate critical supply chain fragility.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class SupplierRiskSegmenter:
    """
    Executes unsupervised clustering on vendor performance data.
    Utilizes RobustScaler and logarithmic transformation to neutralize extreme outliers.
    """

    def segment(self, valid_df: pd.DataFrame, invalid_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute risk tiers utilizing geometric centroid magnitude evaluation.

        Args:
            valid_df (pd.DataFrame): Vendor matrix meeting statistical volume thresholds.
            invalid_df (pd.DataFrame): Vendor matrix violating volume thresholds.

        Returns:
            pd.DataFrame: Unified DataFrame appended with 'risk_tier' classifications.
        """
        if len(valid_df) < 3:
            logger.warning("Insufficient overall vendor volume for K-Means execution. Bypassing clustering.")
            valid_df_copy = valid_df.copy()
            valid_df_copy['risk_tier'] = 'Unclassified'
            invalid_df_copy = invalid_df.copy()
            invalid_df_copy['risk_tier'] = 'Insufficient Data'
            return pd.concat([valid_df_copy, invalid_df_copy], ignore_index=True)

        df = valid_df.copy()

        # 95th Percentile Capping to prevent centroid monopolization
        cap_cols = ['total_spend_volume', 'median_lead_time', 'std_lead_time']
        for col in cap_cols:
            cap_val = df[col].quantile(0.95)
            df[f'{col}_capped'] = np.where(df[col] > cap_val, cap_val, df[col])

        # Mathematical Normalization Matrix
        features = pd.DataFrame()
        # Log transformation normalizes the financial Pareto curve
        features['spend_log'] = np.log1p(np.maximum(df['total_spend_volume_capped'], 0))
        features['lt_median'] = df['median_lead_time_capped']
        features['lt_std'] = df['std_lead_time_capped']

        # IQR Scaling negates remaining extreme variables
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(features)

        n_clusters = 3 if len(df) >= 3 else len(df)
        model = KMeans(n_clusters=n_clusters, init='k-means++', n_init=20, random_state=42)
        labels = model.fit_predict(X_scaled)

        if n_clusters > 1:
            sil_score = silhouette_score(X_scaled, labels)
            if sil_score < 0.5:
                logger.warning("K-Means Silhouette Score %.2f indicates severe cluster overlap.", sil_score)

        # Deterministic Geometry Resolution
        # Calculates composite operational failure magnitude per centroid
        centroids = model.cluster_centers_
        magnitudes = centroids[:, 1] + centroids[:, 2]

        sorted_indices = np.argsort(magnitudes)
        tier_mapping = {}
        tiers = ['Low Risk', 'Medium Risk', 'High Risk'] if n_clusters == 3 else ['Low Risk', 'High Risk']

        for rank, original_idx in enumerate(sorted_indices):
            tier_mapping[original_idx] = tiers[rank]

        df['risk_tier'] = [tier_mapping[label] for label in labels]
        df.drop(columns=[f'{c}_capped' for c in cap_cols], inplace=True)

        invalid_df_copy = invalid_df.copy()
        invalid_df_copy['risk_tier'] = 'Insufficient Data'

        return pd.concat([df, invalid_df_copy], ignore_index=True)