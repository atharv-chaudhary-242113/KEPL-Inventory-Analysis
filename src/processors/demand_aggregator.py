# src/processors/demand_aggregator.py
"""
Demand Aggregator module.

Condenses longitudinal billing data into functional metrics for demand forecasting.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DemandAggregator:
    """
    Class dedicated to computing temporal consumption metrics based on verified ledger transactions.
    """

    def compute(self, pv_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate final purchase transactions.

        Args:
            pv_df (pd.DataFrame): Validated Purchase Vouchers dataset.

        Returns:
            pd.DataFrame: Computed aggregate baseline requirements.
        """
        if pv_df.empty:
            return pd.DataFrame()

        months_covered: int = pv_df['Date'].dt.to_period('M').nunique()
        if months_covered == 0:
            months_covered = 1

        agg_df = pv_df.groupby(['Item Details', 'Particulars', 'Unit']).apply(
            lambda x: pd.Series({
                'total_qty': x['Qty.'].sum(),
                'total_value': x['Amount'].sum(),
                'avg_unit_price': x['Amount'].sum() / x['Qty.'].sum() if x['Qty.'].sum() > 0 else 0.0,
            })
        ).reset_index()

        agg_df['months_covered'] = months_covered
        agg_df['avg_monthly_qty'] = agg_df['total_qty'] / months_covered
        agg_df['avg_quarterly_qty'] = agg_df['avg_monthly_qty'] * 3

        zero_demand_mask = agg_df['avg_monthly_qty'] == 0
        for item in agg_df.loc[zero_demand_mask, 'Item Details']:
            logger.warning("Item '%s' has avg_monthly_qty=0 after filtering. Reorder qty will be 0.", item)

        return agg_df