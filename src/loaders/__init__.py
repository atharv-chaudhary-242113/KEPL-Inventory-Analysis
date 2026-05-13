# src/loaders/__init__.py
"""
Data Loaders Interface.

This module exposes the data loading classes responsible for ingesting
various procurement datasets into the pipeline.
"""

from .base_loader import BaseLoader
from .grn_loader import GRNLoader
from .pov_loader import POVLoader
from .pv_loader import PVLoader
from .closing_stock_loader import ClosingStockLoader

__all__ = [
    "BaseLoader",
    "GRNLoader",
    "POVLoader",
    "PVLoader",
    "ClosingStockLoader"
]