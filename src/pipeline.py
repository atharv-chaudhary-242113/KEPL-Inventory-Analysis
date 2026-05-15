# src/pipeline.py
"""
Orchestration Pipeline module.
"""

import gc
import logging
import time
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

from .loaders import POVLoader, GRNLoader, PVLoader, ClosingStockLoader
from .processors import (DataCleaner, ItemLinker, LeadTimeCalculator,
                         LeadTimePredictor, DemandAggregator, SupplierAggregator)
from .processors.similarity import SemanticSimilarityStrategy
from .processors.anomaly_extractor import AnomalyExtractor
from .analysis import (ABCClassifier, SimpleForecastStrategy,
                       StockAdjustedForecastStrategy, SupplierRiskSegmenter,
                       XGBoostForecastStrategy)
from .exporters import ExcelExporter

logger = logging.getLogger(__name__)


class PipelineConfig:
    def __init__(self, is_lite_mode=True):
        self.is_lite_mode = is_lite_mode
        self.batch_size = 1000 if self.is_lite_mode else 10000

    def reclaim_memory(self, *data_objects):
        """Forces immediate garbage collection for 4GB constraints."""
        if self.is_lite_mode:
            for obj in data_objects:
                if obj is not None:
                    del obj
            gc.collect()


class AnalysisPipeline:
    """
    Central execution controller integrating all system components.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config: dict[str, Any] = config

    def _validate_paths(self) -> None:
        required_keys = ['pov_path', 'grn_path', 'pv_path']
        for key in required_keys:
            path_str = self.config.get(key)
            if not path_str or not Path(path_str).exists():
                raise FileNotFoundError(f"Required input file missing: {path_str}")

    def prepare_clean_data(self, config: PipelineConfig) -> dict[str, pd.DataFrame]:
        """
        Unified ingestion and semantic deduplication block.
        Ensures training and inference evaluate identical token spaces.
        """
        self._validate_paths()

        # 1. Load & Downcast
        pov_df = POVLoader().load(self.config['pov_path'])
        grn_df = GRNLoader().load(self.config['grn_path'])
        pv_df = PVLoader().load(self.config['pv_path'])

        datasets = {'POV': pov_df, 'GRN': grn_df, 'PV': pv_df}
        clean_datasets = {}

        for name, df in datasets.items():
            df = DataCleaner.forward_fill_voucher_fields(df)
            df = DataCleaner.cast_numeric_columns(df)
            df = DataCleaner.drop_non_item_rows(df)
            df = DataCleaner.normalise_item_names(df)
            clean_datasets[name] = df

        config.reclaim_memory(pov_df, grn_df, pv_df, datasets)

        # 2. Semantic Deduplication applied directly to baseline matrices
        similarity_strategy = SemanticSimilarityStrategy()
        DataCleaner.flag_similar_entities(clean_datasets['PV'], 'Particulars', similarity_strategy, threshold=0.85)
        DataCleaner.flag_similar_entities(clean_datasets['POV'], 'Particulars', similarity_strategy, threshold=0.85)
        DataCleaner.flag_similar_entities(clean_datasets['GRN'], 'Particulars', similarity_strategy, threshold=0.85)

        return clean_datasets

    def run(self) -> dict[str, Any]:
        start_time = time.time()
        logger.info("Starting analysis pipeline")

        is_lite_mode = self.config.get('is_lite_mode', True)
        config = PipelineConfig(is_lite_mode=is_lite_mode)

        # Execute shared data prep stage
        clean_datasets = self.prepare_clean_data(config)

        pov_clean = clean_datasets['POV']
        grn_clean = clean_datasets['GRN']
        pv_clean = clean_datasets['PV']

        cs_path = self.config.get('closing_stock_path')
        cs_freq = self.config.get('closing_stock_freq', 'monthly')
        closing_stock_df = ClosingStockLoader(frequency=cs_freq).load(cs_path) if cs_path else None

        # 3. Linkage and Lead Time
        linker = ItemLinker(day_window=self.config.get('lead_time_day_window', 14))
        linked_df = linker.link(pov_clean, grn_clean, pv_clean)
        lt_calculator = LeadTimeCalculator()
        lt_stats = lt_calculator.compute(linked_df)

        # 4. Exceptions Extraction
        anomaly_extractor = AnomalyExtractor()
        exceptions_df = anomaly_extractor.extract_exceptions(pov_clean, grn_clean)

        # 5. ML Time Series Forecast Strategy Resolution
        aggregator = DemandAggregator()
        aggregated_df = aggregator.compute(pv_clean)

        thresh_a = self.config.get('abc_threshold_a', 70.0)
        thresh_b = self.config.get('abc_threshold_b', 90.0)
        abc_classifier = ABCClassifier(threshold_a=thresh_a, threshold_b=thresh_b)
        abc_df = abc_classifier.classify(aggregated_df)

        growth_rate = self.config.get('growth_rate', 1.30)
        base_strategy_cls = StockAdjustedForecastStrategy if closing_stock_df is not None else SimpleForecastStrategy
        base_strategy = base_strategy_cls(growth_rate=growth_rate)

        # Dependency Injection for ML Models
        use_xgboost = self.config.get('use_xgboost', False)
        models_dir = self.config.get('models_dir')

        if use_xgboost and models_dir:
            strategy = XGBoostForecastStrategy(
                models_dir=models_dir,
                fallback_strategy=base_strategy,
                growth_rate=growth_rate
            )
        else:
            strategy = base_strategy

        try:
            forecast_df = strategy.compute(abc_df, closing_stock_df)
        except NotImplementedError as e:
            logger.warning("%s Falling back to base strategy.", str(e))
            forecast_df = base_strategy.compute(abc_df, closing_stock_df)

        config.reclaim_memory(aggregated_df, abc_df)

        # 6. Supplier Risk Segmentation
        supp_aggregator = SupplierAggregator()
        valid_supp, invalid_supp = supp_aggregator.aggregate(pv_clean, linked_df)
        risk_segmenter = SupplierRiskSegmenter()
        supplier_risk_df = risk_segmenter.segment(valid_supp, invalid_supp)

        config.reclaim_memory(valid_supp, invalid_supp, linked_df)

        # 7. Compile Results and Export

        # Dynamically append ML columns if present to uphold Open-Closed Principle
        core_cols = ['Item Details', 'Particulars', 'Unit']
        ml_cols = ['Forecast_Algorithm', 'Backtest_MAPE_%']
        present_ml_cols = [col for col in ml_cols if col in forecast_df.columns]

        monthly_cols = core_cols + ['monthly_reorder_qty'] + present_ml_cols
        quarterly_cols = core_cols + ['quarterly_reorder_qty'] + present_ml_cols

        results = {
            'abc_classification': forecast_df,
            'monthly_forecast': forecast_df[monthly_cols],
            'quarterly_forecast': forecast_df[quarterly_cols],
            'lead_times': lt_stats,
            'exceptions': exceptions_df,
            'supplier_risk_report': supplier_risk_df,
            'anomaly_report': pd.DataFrame(),
            'raw_grn': grn_clean,
            'raw_pov': pov_clean,
            'raw_pv': pv_clean,
        }

        # Calculate Date Bounds
        date_min = pv_clean['Date'].min() if 'Date' in pv_clean.columns and not pv_clean.empty else None
        date_max = pv_clean['Date'].max() if 'Date' in pv_clean.columns and not pv_clean.empty else None

        # Calculate Classification Distribution
        class_counts = forecast_df['abc_class'].value_counts() if 'abc_class' in forecast_df.columns else {}

        duration = time.time() - start_time
        results['summary_metadata'] = {
            'Date Range Start': str(date_min.date()) if date_min is not pd.NaT and date_min else 'N/A',
            'Date Range End': str(date_max.date()) if date_max is not pd.NaT and date_max else 'N/A',
            'Total Items Processed': len(forecast_df),
            'Class A Items': int(class_counts.get('A', 0)),
            'Class B Items': int(class_counts.get('B', 0)),
            'Class C Items': int(class_counts.get('C', 0)),
            'Execution Time (s)': round(duration, 2)
        }

        output_path = self.config.get('output_path')
        if output_path:
            exporter = ExcelExporter(config=self.config)
            exporter.export(results, output_path)

        logger.info("Analysis complete in %.2fs", duration)
        return results