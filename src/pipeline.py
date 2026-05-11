# src/pipeline.py
import logging
from typing import Dict, Optional
import pandas as pd

from .loaders.tally_loader import POVLoader, GRNLoader, PVLoader, ClosingStockLoader
from .processors.item_linker import ItemLinker
from .processors.lead_time_calculator import LeadTimeCalculator
from .processors.demand_aggregator import DemandAggregator
from .analysis.abc_classifier import ABCClassifier
from .analysis.simple_forecast import SimpleForecastStrategy
from .analysis.stock_adjusted_forecast import StockAdjustedForecastStrategy
from .exporters.excel_exporter import ExcelExporter

logger = logging.getLogger("kepl_pipeline")


class AnalysisPipeline:
    """
    Core orchestrator coordinating data ingestion, processing, analysis, and export.
    Demonstrates Dependency Inversion and high-level module design.
    """

    def __init__(self, config: Dict[str, str]):
        """
        Initializes pipeline with configuration parameters.

        Args:
            config (Dict[str, str]): Dictionary containing file paths and execution parameters.
        """
        self.config = config

    def run(self) -> None:
        """
        Executes the end-to-end analytical sequence.
        """
        logger.info("Initiating Analysis Pipeline.")

        # Ingestion Layer
        pov_df = POVLoader().load(self.config.get('pov_path'))
        grn_df = GRNLoader().load(self.config.get('grn_path'))
        pv_df = PVLoader().load(self.config.get('pv_path'))

        cs_path = self.config.get('closing_stock_path')
        cs_df = ClosingStockLoader().load(cs_path) if cs_path else None

        # Processing Layer
        linked_df = ItemLinker.link_pov_and_grn(pov_df, grn_df)
        lead_times_df = LeadTimeCalculator.calculate(linked_df)

        aggregated_demand = DemandAggregator.aggregate(pv_df)

        # Analysis Layer
        classifier = ABCClassifier(
            threshold_a=float(self.config.get('abc_a', 70.0)),
            threshold_b=float(self.config.get('abc_b', 90.0))
        )
        abc_df = classifier.classify(aggregated_demand)

        # Strategy Selection (OCP)
        if cs_df is not None and not cs_df.empty:
            forecast_strategy = StockAdjustedForecastStrategy()
        else:
            forecast_strategy = SimpleForecastStrategy()

        forecast_df = forecast_strategy.compute(abc_df, cs_df)

        # Export Layer
        export_data = {
            'ABC Classification': abc_df,
            'Forecast Output': forecast_df,
            'Lead Times': lead_times_df,
            'Raw PV': pv_df
        }

        exporter = ExcelExporter()
        exporter.export(export_data, self.config.get('output_path', 'output/report.xlsx'))

        logger.info("Analysis Pipeline execution complete.")