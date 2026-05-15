# src/processors/anomaly_extractor.py
"""
Anomaly Extractor module.

Isolates orphaned procurement records (e.g., pending deliveries or unordered receipts)
by executing a relational anti-join on the supply documents.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class AnomalyExtractor:
    """
    Class dedicated to capturing supply chain exceptions without polluting core metrics.
    """

    def extract_exceptions(self, pov_df: pd.DataFrame, grn_df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify records failing the inner merge condition.

        Args:
            pov_df (pd.DataFrame): Purchase Order Vouchers.
            grn_df (pd.DataFrame): Goods Received Notes.

        Returns:
            pd.DataFrame: Unmatched records tagged with an anomaly classification.
        """
        if pov_df.empty and grn_df.empty:
            return pd.DataFrame()

        # Isolate base columns to prevent memory overflow during outer join
        pov_base: pd.DataFrame = pov_df[['Date', 'Vch/Bill No', 'Particulars', 'Item Details', 'Qty.']].copy()
        grn_base: pd.DataFrame = grn_df[['Date', 'Vch/Bill No', 'Particulars', 'Item Details', 'Qty.']].copy()

        pov_base.rename(columns={'Date': 'POV_Date', 'Vch/Bill No': 'POV_No', 'Qty.': 'POV_Qty'}, inplace=True)
        grn_base.rename(columns={'Date': 'GRN_Date', 'Vch/Bill No': 'GRN_No', 'Qty.': 'GRN_Qty'}, inplace=True)

        # Execute outer join with indicator to track data lineage
        merged: pd.DataFrame = pd.merge(
            pov_base,
            grn_base,
            on=['Item Details', 'Particulars'],
            how='outer',
            indicator=True
        )

        # Anti-join condition: Drop 'both' (handled by ItemLinker)
        exceptions: pd.DataFrame = merged[merged['_merge'] != 'both'].copy()

        # Map the internal merge state to operational terminology
        exceptions['Anomaly_Type'] = exceptions['_merge'].map({
            'left_only': 'Pending Delivery (PO missing GRN)',
            'right_only': 'Unordered Delivery (GRN missing PO)'
        })

        exceptions.drop(columns=['_merge'], inplace=True)

        logger.info("Extracted %d orphaned procurement exceptions.", len(exceptions))

        return exceptions