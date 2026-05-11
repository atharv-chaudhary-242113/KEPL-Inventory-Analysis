# src/analysis/abc_classifier.py
import pandas as pd
import logging

logger = logging.getLogger("kepl_pipeline")


class ABCClassifier:
    def __init__(self, threshold_a: float = 70.0, threshold_b: float = 90.0):
        self.threshold_a = threshold_a
        self.threshold_b = threshold_b

    def classify(self, aggregated_df: pd.DataFrame) -> pd.DataFrame:
        df = aggregated_df.copy()
        df = df.sort_values(by='total_value', ascending=False).reset_index(drop=True)

        grand_total = df['total_value'].sum()
        if grand_total == 0:
            logger.warning("Grand total value is 0. Cannot perform ABC classification.")
            df['cumulative_value_pct'] = 0
            df['abc_class'] = 'C'
            df['value_rank'] = df.index + 1
            return df

        df['cumulative_value_pct'] = (df['total_value'].cumsum() / grand_total) * 100

        conditions = [
            (df['cumulative_value_pct'] <= self.threshold_a),
            (df['cumulative_value_pct'] > self.threshold_a) & (df['cumulative_value_pct'] <= self.threshold_b),
            (df['cumulative_value_pct'] > self.threshold_b)
        ]
        choices = ['A', 'B', 'C']
        df['abc_class'] = np.select(conditions, choices, default='C')
        df['value_rank'] = df.index + 1

        logger.info(
            f"ABC Classification complete. A: {len(df[df['abc_class'] == 'A'])}, B: {len(df[df['abc_class'] == 'B'])}, C: {len(df[df['abc_class'] == 'C'])}")
        return df