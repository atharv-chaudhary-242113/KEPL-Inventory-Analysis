# src/analysis/supplier_risk_segmenter.py
"""
Supplier Risk Segmenter module.

Applies dynamic unsupervised clustering and deterministic risk scoring fallbacks
to vendor performance vectors to isolate critical supply chain fragility.
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
    Executes adaptive performance tiering on vendor data.
    Optimizes cluster cohesion dynamically, falling back to a deterministic
    quantile scoring matrix if unsupervised separation boundaries overlap severely.
    """

    def segment(self, valid_df: pd.DataFrame, invalid_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute risk tiers utilizing dynamic geometric clustering or deterministic quantile scoring.

        Args:
            valid_df (pd.DataFrame): Vendor matrix meeting statistical volume thresholds.
            invalid_df (pd.DataFrame): Vendor matrix violating volume thresholds.

        Returns:
            pd.DataFrame: Unified DataFrame appended with 'risk_tier' classifications.
        """
        if len(valid_df) < 3:
            logger.warning("Insufficient overall vendor volume for analytical segmentation. Bypassing execution.")
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

        # Feature Extraction Space
        features = pd.DataFrame()
        features['spend_log'] = np.log1p(np.maximum(df['total_spend_volume_capped'], 0))
        features['lt_median'] = df['median_lead_time_capped']
        features['lt_std'] = df['std_lead_time_capped']

        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(features)

        # Dynamic Optimization Loop for K Selection
        best_sil_score = -1.0
        best_k = 3
        best_labels = None

        max_k = min(4, len(df))
        candidate_k_values = [k for k in range(2, max_k + 1)]

        for k in candidate_k_values:
            model = KMeans(n_clusters=k, init='k-means++', n_init=20, random_state=42)
            labels = model.fit_predict(X_scaled)
            sil = silhouette_score(X_scaled, labels)

            if sil > best_sil_score:
                best_sil_score = sil
                best_k = k
                best_labels = labels

        # Threshold Gate: If optimal silhouette score remains low, trigger deterministic fallback
        SILHOUETTE_THRESHOLD = 0.35
        if best_sil_score < SILHOUETTE_THRESHOLD:
            logger.warning(
                "Optimal Silhouette Score (%.2f) below threshold (%s) under K-Means. "
                "Executing deterministic Quantile Scoring Matrix fallback to mitigate artificial boundary allocation.",
                best_sil_score, SILHOUETTE_THRESHOLD
            )
            df['risk_tier'] = self._compute_deterministic_tiers(df)
        else:
            logger.info("Executing K-Means segment clustering with optimal K=%d (Silhouette Score: %.2f)", best_k,
                        best_sil_score)

            model = KMeans(n_clusters=best_k, init='k-means++', n_init=20, random_state=42)
            labels = model.fit_predict(X_scaled)
            centroids = model.cluster_centers_

            # Risk magnitude metrics derivation based on operational parameters
            magnitudes = centroids[:, 1] + centroids[:, 2]
            sorted_indices = np.argsort(magnitudes)

            tier_mapping = {}
            if best_k == 4:
                tiers = ['Low Risk', 'Medium-Low Risk', 'Medium-High Risk', 'High Risk']
            elif best_k == 3:
                tiers = ['Low Risk', 'Medium Risk', 'High Risk']
            else:
                tiers = ['Low Risk', 'High Risk']

            for rank, original_idx in enumerate(sorted_indices):
                tier_mapping[original_idx] = tiers[rank]

            df['risk_tier'] = [tier_mapping[label] for label in labels]

        df.drop(columns=[f'{c}_capped' for c in cap_cols], inplace=True)

        invalid_df_copy = invalid_df.copy()
        invalid_df_copy['risk_tier'] = 'Insufficient Data'

        return pd.concat([df, invalid_df_copy], ignore_index=True)

    def _compute_deterministic_tiers(self, df: pd.DataFrame) -> list[str]:
        """
        Calculates clear, rule-based supplier risk tiers using data rank quantiles.
        Higher lead times and higher standard deviations yield increased scores,
        while larger spend volume dampens risk category boundaries due to vendor strategic value.
        """
        spend_pct = df['total_spend_volume'].rank(pct=True)
        lt_med_pct = df['median_lead_time'].rank(pct=True)
        lt_std_pct = df['std_lead_time'].fillna(df['std_lead_time'].median()).rank(pct=True)

        # Composite score formulation weighting operational risk parameters at 80% and volume at 20%
        composite_score = (lt_med_pct * 0.40) + (lt_std_pct * 0.40) + ((1.0 - spend_pct) * 0.20)

        tiers = []
        for score in composite_score:
            if score <= 0.33:
                tiers.append('Low Risk')
            elif score <= 0.66:
                tiers.append('Medium Risk')
            else:
                tiers.append('High Risk')
        return tiers