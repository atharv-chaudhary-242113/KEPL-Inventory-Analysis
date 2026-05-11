# src/exporters/base_exporter.py
from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd


class BaseExporter(ABC):
    """
    Abstract interface for output generation.
    Enforces Dependency Inversion and OCP.
    """

    @abstractmethod
    def export(self, results: Dict[str, pd.DataFrame], output_path: str) -> None:
        """
        Exports the analysis results to a specified format.

        Args:
            results (Dict[str, pd.DataFrame]): Dictionary mapped to resultant dataframes.
            output_path (str): Filepath for the generated artifact.
        """
        pass