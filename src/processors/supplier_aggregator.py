# src/processors/supplier_aggregator.py
"""
Supplier Aggregator module.

Extracts and unifies supplier financial volume and temporal delivery performance
into a two-dimensional mathematical matrix for unsupervised clustering.
"""

import pandas as pd


class SupplierAggregator:
    """
    Constructs the operational feature matrix per vendor.
    Adheres to the Single Responsibility Principle by isolating dataframe joins
    from machine learning operations.
    """

    def aggregate(self, pv_df: pd.DataFrame, linked_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Merge discrete financial and operational DataFrames.

        Args:
            pv_df (pd.DataFrame): Validated Purchase Vouchers dataset.
            linked_df (pd.DataFrame): Temporal POV-to-GRN linked events.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]:
                - Valid suppliers matrix (observations >= 3).
                - Invalid suppliers matrix (insufficient data bypass).
        """
        if pv_df.empty or linked_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Isolate financial magnitude
        spend = pv_df.groupby('Particulars')['Amount'].sum().reset_index()
        spend.rename(columns={'Amount': 'total_spend_volume'}, inplace=True)

        # Isolate temporal variance
        lt_stats = linked_df.groupby('Particulars')['lead_time_days'].agg(
            median_lead_time='median',
            std_lead_time='std',
            observation_count='count'
        ).reset_index()

        merged: pd.DataFrame = pd.merge(spend, lt_stats, on='Particulars', how='inner')

        # Structural Bypass: Prevent artificial zero-variance imputation
        mask = merged['observation_count'] >= 3
        valid_df = merged[mask].copy()
        invalid_df = merged[~mask].copy()

        return valid_df, invalid_df