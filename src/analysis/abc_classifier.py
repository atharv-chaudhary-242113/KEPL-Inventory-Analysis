# src/analysis/abc_classifier.py
"""
ABC Classification module.

Executes Pareto-based inventory classification determined by cumulative consumption value.
"""

import pandas as pd


class ABCClassifier:
    """
    Assigns A, B, or C classifications to inventory items based on aggregate expenditure.
    """

    def __init__(self, threshold_a: float = 70.0, threshold_b: float = 90.0) -> None:
        """
        Initialize classification boundaries.

        Args:
            threshold_a (float): Upper cumulative percentage limit for Class A items.
            threshold_b (float): Upper cumulative percentage limit for Class B items.
        """
        self.threshold_a: float = threshold_a
        self.threshold_b: float = threshold_b

    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply classification logic to the aggregated consumption dataframe.

        Args:
            df (pd.DataFrame): Dataframe containing a 'total_value' column.

        Returns:
            pd.DataFrame: Dataframe appended with 'abc_class', 'cumulative_value_pct', and 'value_rank'.
        """
        if df.empty or 'total_value' not in df.columns:
            return df

        df_sorted: pd.DataFrame = df.sort_values(by='total_value', ascending=False).copy()
        grand_total: float = df_sorted['total_value'].sum()

        if grand_total == 0:
            df_sorted['cumulative_value_pct'] = 0.0
            df_sorted['abc_class'] = 'C'
            df_sorted['value_rank'] = range(1, len(df_sorted) + 1)
            return df_sorted

        df_sorted['cumulative_value_pct'] = (df_sorted['total_value'].cumsum() / grand_total) * 100.0
        df_sorted['value_rank'] = range(1, len(df_sorted) + 1)

        def assign_class(pct: float) -> str:
            if pct <= self.threshold_a:
                return 'A'
            elif pct <= self.threshold_b:
                return 'B'
            return 'C'

        df_sorted['abc_class'] = df_sorted['cumulative_value_pct'].apply(assign_class)
        return df_sorted