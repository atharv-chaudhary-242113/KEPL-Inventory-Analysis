# src/processors/item_linker.py
"""
Item Linker module.

Provides relational mapping between discrete procurement documents to establish
empirical traceability and performance metrics.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ItemLinker:
    """
    Class responsible for integrating POV, GRN, and PV datasets across temporal windows.
    """

    def __init__(self, day_window: int = 14) -> None:
        """
        Initialize the linker with specific temporal constraints.

        Args:
            day_window (int): Acceptable lead delay threshold.
        """
        self.day_window: int = day_window

    def link(self, pov_df: pd.DataFrame, grn_df: pd.DataFrame, pv_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge discrete voucher streams to compute fulfilled delivery metrics.

        Args:
            pov_df (pd.DataFrame): Purchase Order Vouchers.
            grn_df (pd.DataFrame): Goods Received Notes.
            pv_df (pd.DataFrame): Purchase Vouchers.

        Returns:
            pd.DataFrame: Unified DataFrame containing combined linkage fields and 'lead_time_days'.
        """
        if pov_df.empty or grn_df.empty:
            return pd.DataFrame()

        pov_base: pd.DataFrame = pov_df[['Date', 'Vch/Bill No', 'Particulars', 'Item Details', 'Qty.']].copy()
        grn_base: pd.DataFrame = grn_df[['Date', 'Vch/Bill No', 'Particulars', 'Item Details', 'Qty.']].copy()

        pov_base.rename(columns={'Date': 'POV_Date', 'Vch/Bill No': 'POV_No', 'Qty.': 'POV_Qty'}, inplace=True)
        grn_base.rename(columns={'Date': 'GRN_Date', 'Vch/Bill No': 'GRN_No', 'Qty.': 'GRN_Qty'}, inplace=True)

        merged: pd.DataFrame = pd.merge(
            pov_base, grn_base,
            on=['Item Details', 'Particulars'],
            how='inner'
        )

        merged['lead_time_days'] = (merged['GRN_Date'] - merged['POV_Date']).dt.days

        temporal_mask: pd.Series = (merged['lead_time_days'] >= 0) & (merged['lead_time_days'] <= self.day_window)
        qty_mask: pd.Series = merged['GRN_Qty'] <= (merged['POV_Qty'] * 2.0)

        valid_links: pd.DataFrame = merged[temporal_mask & qty_mask].copy()

        return valid_links