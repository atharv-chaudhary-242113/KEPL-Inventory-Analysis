# src/pipeline.py
"""
Orchestration Pipeline module.

Executes the end-to-end analytical protocol. Coordinates data ingestion,
cleaning, demand aggregation, predictive modeling, anomaly detection,
forecasting, and final export.
"""

import logging
import time
from pathlib import Path
from typing import Any
import pandas as pd

from .loaders import POVLoader, GRNLoader, PVLoader, ClosingStockLoader
from .processors import DataCleaner, ItemLinker, LeadTimeCalculator, LeadTimePredictor, DemandAggregator
from .processors.similarity import SemanticSimilarityStrategy
from .processors.anomaly_extractor import AnomalyExtractor
from .analysis import ABCClassifier, AnomalyDetector, SimpleForecastStrategy, StockAdjustedForecastStrategy
from .exporters import ExcelExporter


logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Central execution controller integrating all system components while
    strictly adhering to the Single Responsibility Principle.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the pipeline with structural constraints.

        Args:
            config (dict[str, Any]): Dictionary containing file paths, output locations,
                                     thresholds, and execution flags.
        """
        self.config: dict[str, Any] = config

    def _validate_paths(self) -> None:
        """
        Verify the existence of all mandatory input files prior to execution.

        Raises:
            FileNotFoundError: If a required source document is missing.
        """
        required_keys = ['pov_path', 'grn_path', 'pv_path']
        for key in required_keys:
            path_str = self.config.get(key)
            if not path_str or not Path(path_str).exists():
                raise FileNotFoundError(f"Required input file missing: {path_str}")

    def run(self) -> dict[str, Any]:
        """
        Execute the primary analytical protocol.

        Returns:
            dict[str, Any]: Dictionary containing all computed dataframes and execution metrics.
        """
        start_time = time.time()
        logger.info("Starting analysis pipeline")

        self._validate_paths()

        # Step 2: Ingestion
        pov_df = POVLoader().load(self.config['pov_path'])
        grn_df = GRNLoader().load(self.config['grn_path'])
        pv_df = PVLoader().load(self.config['pv_path'])

        cs_path = self.config.get('closing_stock_path')
        cs_freq = self.config.get('closing_stock_freq', 'monthly')
        closing_stock_df = ClosingStockLoader(frequency=cs_freq).load(cs_path)

        # Step 3: Cleaning
        datasets = {'POV': pov_df, 'GRN': grn_df, 'PV': pv_df}
        clean_datasets = {}

        # Instantiate similarity strategy
        similarity_strategy = SemanticSimilarityStrategy()

        for name, df in datasets.items():
            df = DataCleaner.forward_fill_voucher_fields(df)
            df = DataCleaner.cast_numeric_columns(df)
            df = DataCleaner.drop_non_item_rows(df)
            df = DataCleaner.normalise_item_names(df)

            # Item Details duplication check purged. Absolute nomenclature enforced.
            DataCleaner.flag_similar_entities(df, 'Particulars', similarity_strategy, threshold=0.85)

            clean_datasets[name] = df

        # Restore strict variable assignments for downstream processing
        pov_clean = clean_datasets['POV']
        grn_clean = clean_datasets['GRN']
        pv_clean = clean_datasets['PV']

        # Step 4: Demand Aggregation
        aggregator = DemandAggregator()
        aggregated_df = aggregator.compute(pv_clean)

        # Step 5: ABC Classification
        thresh_a = self.config.get('abc_threshold_a', 70.0)
        thresh_b = self.config.get('abc_threshold_b', 90.0)
        abc_classifier = ABCClassifier(threshold_a=thresh_a, threshold_b=thresh_b)
        abc_df = abc_classifier.classify(aggregated_df)

        # Step 6: Linkage and Lead Time Computation
        linker = ItemLinker(day_window=self.config.get('lead_time_day_window', 14))
        linked_df = linker.link(pov_clean, grn_clean, pv_clean)

        lt_calculator = LeadTimeCalculator()
        lt_stats = lt_calculator.compute(linked_df)

        # Step 6.5: Exception Extraction (Anti-Join)
        anomaly_extractor = AnomalyExtractor()
        exceptions_df = anomaly_extractor.extract_exceptions(pov_clean, grn_clean)

        # Step 7: Predictive Modeling
        lt_predictor = LeadTimePredictor()
        lt_predictor.train_or_load(linked_df, lt_stats)

        # Step 8: Anomaly Detection (Prices)
        anomaly_detector = AnomalyDetector(contamination=self.config.get('anomaly_contamination', 'auto'))
        anomaly_df = anomaly_detector.detect(pv_clean)

        # Step 9: Forecasting Strategy Resolution
        growth_rate = self.config.get('growth_rate', 1.30)
        if closing_stock_df is not None:
            strategy = StockAdjustedForecastStrategy(growth_rate=growth_rate)
        else:
            strategy = SimpleForecastStrategy(growth_rate=growth_rate)

        try:
            forecast_df = strategy.compute(abc_df, closing_stock_df)
        except NotImplementedError as e:
            logger.warning("%s Falling back to SimpleForecastStrategy.", str(e))
            strategy = SimpleForecastStrategy(growth_rate=growth_rate)
            forecast_df = strategy.compute(abc_df, None)

        # Compilation of metrics
        results = {
            'abc_classification': forecast_df,
            'monthly_forecast': forecast_df[['Item Details', 'Particulars', 'Unit', 'monthly_reorder_qty']],
            'quarterly_forecast': forecast_df[['Item Details', 'Particulars', 'Unit', 'quarterly_reorder_qty']],
            'lead_times': lt_stats,
            'exceptions': exceptions_df,
            'anomaly_report': anomaly_df[
                anomaly_df['is_anomaly']] if 'is_anomaly' in anomaly_df.columns else anomaly_df,
            'raw_grn': grn_clean,
            'raw_pov': pov_clean,
            'raw_pv': pv_clean,
        }

        # Monthly breakdown construction
        if 'Date' in pv_clean.columns:
            pv_clean['month_year'] = pv_clean['Date'].dt.to_period('M')
            breakdown = pv_clean.pivot_table(
                index=['Item Details', 'Particulars', 'Unit'],
                columns='month_year',
                values='Qty.',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            breakdown.columns = [str(c) if not isinstance(c, str) else c for c in breakdown.columns]
            results['monthly_breakdown'] = breakdown

        date_min = pv_clean['Date'].min() if not pv_clean.empty else None
        date_max = pv_clean['Date'].max() if not pv_clean.empty else None

        duration = time.time() - start_time
        results['summary_metadata'] = {
            'Date Range Start': str(date_min.date()) if date_min is not pd.NaT and date_min else 'N/A',
            'Date Range End': str(date_max.date()) if date_max is not pd.NaT and date_max else 'N/A',
            'Total Items Processed': len(abc_df),
            'Class A Items': len(abc_df[abc_df['abc_class'] == 'A']) if 'abc_class' in abc_df.columns else 0,
            'Class B Items': len(abc_df[abc_df['abc_class'] == 'B']) if 'abc_class' in abc_df.columns else 0,
            'Class C Items': len(abc_df[abc_df['abc_class'] == 'C']) if 'abc_class' in abc_df.columns else 0,
            'Execution Time (s)': round(duration, 2)
        }

        # Step 10: Export Protocol
        output_path = self.config.get('output_path')
        if output_path:
            exporter = ExcelExporter(config=self.config)
            exporter.export(results, output_path)

        logger.info("Analysis complete in %.2fs", duration)

        return results