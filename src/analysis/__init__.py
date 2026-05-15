# src/analysis/__init__.py
"""
Analysis module.

Exposes analytical components for classification, unsupervised anomaly detection,
forecasting strategies, and supplier risk segmentation.
"""

from .abc_classifier import ABCClassifier
from .base_forecast_strategy import BaseForecastStrategy
from .simple_forecast import SimpleForecastStrategy
from .stock_adjusted_forecast import StockAdjustedForecastStrategy
from .supplier_risk_segmenter import SupplierRiskSegmenter
from .xgboost_forecast import XGBoostForecastStrategy

__all__ = [
    "ABCClassifier",
    "XGBoostForecastStrategy",
    "BaseForecastStrategy",
    "SimpleForecastStrategy",
    "StockAdjustedForecastStrategy",
    "SupplierRiskSegmenter"
]

from .xgboost_forecast import XGBoostForecastStrategy