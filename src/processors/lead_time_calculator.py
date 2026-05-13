# src/processors/lead_time_calculator.py
"""
Lead Time Calculator module.

Aggregates individual procurement linkages to extract statistical lead time distributions.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class LeadTimeCalculator:
    """
    Class dedicated to computing descriptive statistics on delivery timelines.
    """

    def compute(self, linked_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate empirical lead time boundaries per entity pair.

        Args:
            linked_df (pd.DataFrame): Validated, linked procurement events.

        Returns:
            pd.DataFrame: Computed lead time statistics.
        """
        if linked_df.empty or 'lead_time_days' not in linked_df.columns:
            return pd.DataFrame()

        stats = linked_df.groupby(['Item Details', 'Particulars'])['lead_time_days'].agg(
            avg_lead_time_days='mean',
            median_lead_time_days='median',
            min_lead_time_days='min',
            max_lead_time_days='max',
            observation_count='count'
        ).reset_index()

        low_obs_mask = stats['observation_count'] < 3
        for _, row in stats[low_obs_mask].iterrows():
            logger.warning(
                "Unreliable lead time sample size for Item: '%s', Supplier: '%s'. Count: %d",
                row['Item Details'], row['Particulars'], row['observation_count']
            )

        return stats