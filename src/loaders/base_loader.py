# src/loaders/base_loader.py
from abc import ABC, abstractmethod
import pandas as pd

class BaseLoader(ABC):
    @abstractmethod
    def load(self, filepath: str) -> pd.DataFrame:
        pass