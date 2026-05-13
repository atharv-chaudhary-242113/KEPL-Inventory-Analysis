# src/exporters/base_exporter.py
"""
Abstract base exporter module.

Defines the explicit contract required for all report generation strategies.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExporter(ABC):
    """
    Abstract base class enforcing the export interface constraint.
    """

    @abstractmethod
    def export(self, results: dict[str, Any], output_path: str) -> None:
        """
        Write the analytical payload to physical storage.

        Args:
            results (dict[str, Any]): Dictionary containing processed dataframes and metadata.
            output_path (str): Absolute or relative system path for the output file.
        """
        pass