# src/analysis/base_forecast_strategy.py
from abc import ABC, abstractmethod
import pandas as pd

class BaseForecastStrategy(ABC):
    @abstractmethod
    def compute(self, aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame = None) -> pd.DataFrame:
        pass