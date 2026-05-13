# src/exporters/__init__.py
"""
Exporters module.

Exposes components for writing analytical payloads to persistent output formats.
Adheres to the Open/Closed Principle to facilitate future format additions (e.g., CSV, PDF).
"""

from .base_exporter import BaseExporter
from .excel_exporter import ExcelExporter

__all__ = [
    "BaseExporter",
    "ExcelExporter"
]