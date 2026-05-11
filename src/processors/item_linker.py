# src/processors/item_linker.py
import pandas as pd
import logging

logger = logging.getLogger("kepl_pipeline")


class ItemLinker:
    """
    Responsible for linking Purchase Order Vouchers (POV) to Goods Received Notes (GRN).
    Follows Single Responsibility Principle (SRP) by isolating the join logic.
    """

    @staticmethod
    def link_pov_and_grn(pov_df: pd.DataFrame, grn_df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
        """
        Links POV and GRN data using a temporal window join on item details and supplier.

        Args:
            pov_df (pd.DataFrame): Cleaned Purchase Order Vouchers data.
            grn_df (pd.DataFrame): Cleaned Goods Received Notes data.
            window_days (int): Maximum allowable days between order and receipt to consider a match.

        Returns:
            pd.DataFrame: Merged dataframe containing linked orders and receipts.
        """
        if pov_df.empty or grn_df.empty:
            logger.warning("POV or GRN dataframe is empty. Returning empty linked dataframe.")
            return pd.DataFrame()

        # Isolate necessary columns to prevent memory bloat (KISS)
        pov_sub = pov_df[['Date', 'Item Details', 'Particulars', 'Qty.']].copy()
        pov_sub.rename(columns={'Date': 'pov_date', 'Qty.': 'pov_qty'}, inplace=True)

        grn_sub = grn_df[['Date', 'Item Details', 'Particulars', 'Qty.']].copy()
        grn_sub.rename(columns={'Date': 'grn_date', 'Qty.': 'grn_qty'}, inplace=True)

        # Merge on composite key: Item and Supplier
        merged_df = pd.merge(
            pov_sub,
            grn_sub,
            on=['Item Details', 'Particulars'],
            how='inner'
        )

        # Calculate temporal difference
        merged_df['lead_time_days'] = (merged_df['grn_date'] - merged_df['pov_date']).dt.days

        # Filter out invalid temporal matches (negative lead time or beyond window)
        valid_links = merged_df[
            (merged_df['lead_time_days'] >= 0) &
            (merged_df['lead_time_days'] <= window_days)
            ].copy()

        logger.info(f"Successfully linked {len(valid_links)} POV-GRN records within {window_days}-day window.")
        return valid_links