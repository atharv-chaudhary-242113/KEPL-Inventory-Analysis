KEPL Procurement Analytics & Inventory Forecasting System

1. Project Overview

This system is an enterprise-grade Procurement Analytics, Machine Learning Forecasting, and Supplier Risk Analysis System custom-engineered for Khokhar Electricals Pvt. Ltd. (KEPL). The engine ingests transactional exports from accounting software—specifically Purchase Order Vouchers (POV), Goods Received Notes (GRN), and Purchase Vouchers (PV)—to synthesize:

Dynamic ABC Category Classification: Pareto-based stratification of inventory items driven by cumulative consumption value.

Multi-Model Demand Forecasting Ensemble: A dynamic predictive framework combining Baseline Growth-Scaled Averages, Holt-Winters Triple Exponential Smoothing, and Autoregressive XGBoost Regressors to compute optimal monthly and quarterly reorder boundaries.

Unsupervised Supplier Risk Segmentation: Multi-dimensional K-Means clustering of vendor performance metrics with automated deterministic fallback protocols.

Supply Chain Anomaly & Exception Profiling: Outlier transaction flags via Isolation Forests alongside mismatch analytics (anti-joins) targeting orphaned logistics documentation.

PyQt6 Graphical Controller: A highly responsive desktop workspace engineered with non-blocking QThread execution loops and real-time diagnostic output views.

The system adheres to modular software engineering standards, featuring a decoupled, extensible pipeline prepared to absorb supplementary datasets (such as Closing Stock arrays) with zero core-code modifications.

2. Technical Architecture & Design Principles

The application is structured around robust object-oriented patterns, enforcing strict separation of concerns, absolute encapsulation, and memory efficiency under performance-constrained environments.

SOLID Implementation Matrix

Principle

Structural Implementation

S - Single Responsibility

Functional boundaries are isolated. Concrete loaders (POVLoader, GRNLoader, PVLoader) manage parsing. Cleaners (DataCleaner) process string schemas. Strategies (Simple, XGBoost, HoltWinters, DynamicEnsemble) calculate forecasts. Exporters serialize outputs.

O - Open/Closed

Extending the forecast engine or adding ingestion streams requires subclassing abstract interfaces (BaseForecastStrategy, BaseLoader, BaseSimilarityStrategy). The pipeline automatically resolves concrete sub-instances without modifications to AnalysisPipeline.run().

L - Liskov Substitution

All processing strategies accept standardized abstract contracts. If the ML training layer is bypassed, the system seamlessly substitutes the baseline average strategy without breaking execution.

I - Interface Segregation

Front-end controller panels consume specific slice APIs (e.g., training signals via MLTrainingWorker, pipeline diagnostics via standard logging, output rendering through local data models).

D - Dependency Inversion

High-level orchestration (AnalysisPipeline) communicates with data loaders and forecasting layers exclusively through abstract base boundaries, decoupling execution logic from specific storage or UI layouts.

Concurrency Model

To eliminate execution bottlenecks and prevent interface freezing during computation, the system separates the UI layout from mathematical execution.

PipelineWorker subclassing QThread abstracts the standard analytical run.

MLTrainingWorker subclassing QThread manages parallel XGBoost optimization.

Inter-thread communication is strictly governed by thread-safe PyQt signals (pyqtSignal), transmitting serialized metrics back to the main GUI thread. Direct UI modifications from secondary threads are prohibited.

Low-Memory Optimization Protocol (4GB RAM Constraints)

When is_lite_mode is enabled in PipelineConfig, the system deploys proactive resource management techniques:

Programmatic Data Downcasting: Standard 64-bit data allocations are systematically compressed. Floating points are restricted to float32, integers to int16/int32, and high-cardinality nominal text fields with repeated strings are converted to pandas category types.

Streaming Ingestion Control: Row structures are verified and loaded with explicit column constraints, ensuring unallocated attributes do not consume RAM.

Explicit Garbage Collection: High-density intermediate arrays (e.g., unlinked datasets, temporary similarity matrices) are programmatically deleted using del followed by immediate calls to gc.collect() at key execution stages.

3. Ingestion & Data Preparation Layer

Ingest Constraints

All loaders inherit from the abstract BaseLoader. A strict gatekeeper limit of 5 MB is enforced on raw incoming files via _validate_file_size(). If a file exceeds this ceiling, a descriptive ValueError is raised, requesting the operator export a narrower chronological range from Tally.

Parsing & Cleansing Sequence

Row Ingestion: Loader skips administrative metadata (rows 0–5) and parses row 6 as the primary header grid.

Chronological and Vendor Forward-Filling: Tally multi-line vouchers only record transaction dates, voucher numbers, and vendor particulars on the first line item. Subsequent lines are programmatically forward-filled (ffill()) within distinct voucher blocks.

Sanitization Filters: System filters out non-inventory entries (such as administrative freight fees, taxes, or total summaries) by isolating records where the unit of measure is - or where Item Details contains regex matches for freight|tax|charge.

Nominal Standardization: To eliminate string mismatches, product designations and supplier names are systematically stripped of leading/trailing spaces and converted to lowercase.

Semantic Transformer Deduplication

Rather than relying on brittle character-level TF-IDF distances, the system integrates a SemanticSimilarityStrategy deploying the all-MiniLM-L6-v2 Sentence-Transformer model.

Branch-Aware Normalization: The system implements branch metadata extraction. Branch identifiers or geographic qualifiers enclosed in brackets or parentheses (e.g., Supplier A (UP), Supplier A [DL]) are stripped using regex.

Base-Name Identity Matching: The system computes dense embeddings of distinct entities. It checks for highly similar listings (cosine similarity $\ge 0.85$). If their base names match exactly but geographical tags vary, it isolates them as branch duplicates and flags them in the console, protecting financial records from incorrect automated merges.

4. Analytical Engines

ABC Category Stratification

The system applies Pareto sorting mechanics to prioritize inventory items based on financial impact.
Given the set of items $I$, for each item $i \in I$, the total expenditure value $V_i$ is computed as:

$$V_i = \sum \text{Amount}_i$$

Items are sorted in descending order of $V_i$. The cumulative percentage of total expenditure is calculated as:

$$\text{Cumulative Pct}_i = \frac{\sum_{j=1}^{i} V_j}{\sum_{k \in I} V_k} \times 100$$

Using configurable threshold boundaries (defaults: $\theta_A = 70.0$, $\theta_B = 90.0$), the system categorizes inventory:

Class A ($\text{Cumulative Pct}_i \le \theta_A$): High-value assets requiring tight administrative control.

Class B ($\theta_A < \text{Cumulative Pct}_i \le \theta_B$): Medium-value assets.

Class C ($\text{Cumulative Pct}_i > \theta_B$): Low-value maintenance and auxiliary components.

Unsupervised Procurement Anomaly Detection

The system deploys an AnomalyDetector executing the IsolationForest clustering algorithm on final purchase vouchers.

Dimensional Feature Mapping: Isolates transaction features: unit price, transaction volume (Qty.), and time indices (month of the year). The aggregate transaction amount is explicitly omitted to prevent collinearity errors.

Contamination Gate: Employs contamination='auto' to naturally define the classification threshold based on anomalous scores. Outlying data points are automatically recorded in the diagnostic ledger and mapped to the Anomaly Report page in the final Excel output.

5. Advanced Forecasting & Time-Series Suite

Relational Document Mapping (ItemLinker)

Before establishing lead-time and forecast matrices, the engine executes a fuzzy date-window join to link POV -> GRN -> PV records.

Temporal Matching: Matches POV and GRN entries under the same item and supplier names within a configurable timeline window (default: $\pm 14$ days).

Quantity Proximity Matching: Enforces a strict filter where the GRN quantity must be $\le$ twice the initial POV quantity, preventing unrelated transactions within the same temporal window from cross-linking.

Dynamic Ensemble Forecasting Strategy

The forecasting pipeline utilizes a hybrid DynamicEnsembleForecastStrategy to prevent overfitting. It dynamically evaluates and switches forecasting algorithms based on accuracy metrics.

                  +-----------------------------------+
                  |      Aggregated Demand Data       |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
+-----------------------+ +-----------------------+ +-----------------------+
|  Simple Baseline Avg  | |  Holt-Winters Engine  | |    XGBoost Engine     |
| (Growth-Scaled 1.30)  | |  (Triple Smoothing)   | |  (Autoregressive)    |
+-----------------------+ +-----------------------+ +-----------------------+
            |                       |                       |
            +-----------------------+-----------------------+
                                    v
                  +-----------------------------------+
                  | Dynamic Ensemble Selection Layer  |
                  |     (MAPE-Driven Backtesting)     |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |  Selected Reorder Recommendation  |
                  +-----------------------------------+


SimpleForecastStrategy (Baseline): Computes the basic monthly historical average consumption, scaling it by an expected annual growth projection (default: $1.30$, representing $30\%$ annual growth):

$$\text{Monthly Reorder Qty} = \lceil \text{Avg Monthly Qty} \times \text{Growth Rate} \rceil$$

HoltWintersForecastStrategy: Applies triple exponential smoothing models via statsmodels with additive trend and seasonal components. This strategy requires at least two complete seasonal periods ($24$ months of historical data) to run.

XGBoostForecastStrategy: Loads serialized autoregressive XGBRegressor estimators from the models/ directory, predicting demand values for upcoming months using time indices, month integers, and quarter tracking values.

Dynamic Selection Protocol: For every item-supplier pair, the system reviews the backtest Mean Absolute Percentage Error (MAPE). It selects the forecasting model with the lowest MAPE. If ML predictions are missing, uncalibrated, or sparse, the system automatically falls back to the simple baseline average.

Stock-Adjusted Stub

An integrated stub, StockAdjustedForecastStrategy, is built into the pipeline. Once historical closing stock arrays are provided, this module subtracts current stock levels from gross demand to compute net ordering requirements:

$$\text{Net Monthly Demand} = \text{Gross Monthly Demand} - \text{Avg Monthly Closing Stock}$$

If executed without closing stock, the pipeline catches the NotImplementedError, logs a diagnostic warning, and gracefully falls back to the dynamic ensemble model.

6. Unsupervised Supplier Risk Analytics

The SupplierRiskSegmenter uses unsupervised machine learning to classify supplier profiles, evaluating procurement risk and supply chain reliability.

Feature Space Construction

For each supplier, a performance vector is built from actual historical transactions:

Financial Volume: Logarithmic total spend ($\log(1 + \text{total\_spend})$) to handle high-variance distributions.

Operational Latency: Median lead time calculated between matched POV and GRN documents.

Logistics Reliability: Standard deviation of delivery lead times, capturing logistical volatility.

To prevent outliers from skewing the model, features are capped at their 95th percentile and scaled using RobustScaler before clustering.

Dynamic K-Means Optimization

The system dynamically runs K-Means clustering across a range of clusters ($k \in [2, 4]$). It evaluates each configuration by computing the silhouette score:

$$s = \frac{b - a}{\max(a, b)}$$

The configuration yielding the highest silhouette score is selected as the optimal clustering model.

Deterministic Fallback Matrix

If the optimal silhouette score drops below the confidence threshold ($s < 0.35$), the system rejects the K-Means boundaries. It automatically falls back to a deterministic Quantile Scoring Matrix:

Suppliers are ranked by percentiles for median lead time ($P_{\text{LT}}$), standard deviation of lead time ($P_{\text{STD}}$), and total spend volume ($P_{\text{SPEND}}$).

A composite risk metric is computed as:

$$\text{Composite Score} = (P_{\text{LT}} \times 0.40) + (P_{\text{STD}} \times 0.40) + ((1.0 - P_{\text{SPEND}}) \times 0.20)$$

Risk tiers are assigned based on score ranges:

$\text{Score} \le 0.33 \implies \text{Low Risk}$

$0.33 < \text{Score} \le 0.66 \implies \text{Medium Risk}$

$\text{Score} > 0.66 \implies \text{High Risk}$

7. Directory Structure

procurement-analytics/
├── .gitignore
├── README.md
├── pyproject.toml                 # Centralized uv package definition
├── run_gui.py                     # PyQt6 GUI Application Entry Point
├── logs/                          # System execution logs
│   └── app.log
├── models/                        # Serialized XGBoost models (.joblib)
├── output/                        # Default export folder for Excel reports
├── gui/                           # PyQt6 User Interface package
│   ├── __init__.py
│   ├── app.py                     # Main QMainWindow Setup
│   ├── views/
│   │   ├── __init__.py
│   │   ├── file_selection_view.py # File picker interfaces
│   │   ├── log_view.py            # Real-time scrolling diagnostic log terminal
│   │   ├── main_window.py         # App shell (navigation, layout, sidebars)
│   │   ├── ml_training_view.py    # XGBoost training controller
│   │   ├── output_config_view.py  # Run and output path configurations
│   │   └── results_view.py        # Tabular displays & embedded Pareto chart
│   └── widgets/
│       ├── __init__.py
│       ├── abc_chart_widget.py    # Embedded Matplotlib Canvas
│       ├── file_picker.py         # File picker component
│       └── folder_picker.py       # Directory picker component
└── src/                           # Central Analytics Engine
    ├── __init__.py
    ├── logger_config.py           # Logging, formatters, and rotation rules
    ├── pipeline.py                # Main orchestration pipeline
    ├── analysis/                  # Analytics and forecasting strategies
    │   ├── __init__.py
    │   ├── abc_classifier.py      # Pareto ABC classification
    │   ├── anomaly_detector.py    # Isolation Forest transaction anomalies
    │   ├── base_forecast_strategy.py
    │   ├── ensemble_forecast.py   # Dynamic MAPE ensemble selector
    │   ├── holt_winters_forecast.py# Triple Exponential Smoothing
    │   ├── simple_forecast.py     # Growth-scaled baseline forecasts
    │   ├── stock_adjusted_forecast.py
    │   ├── supplier_risk_segmenter.py # Unsupervised K-Means risk clustering
    │   └── xgboost_forecast.py    # XGBoost inference execution
    ├── exporters/                 # Output serialization
    │   ├── __init__.py
    │   ├── base_exporter.py
    │   └── excel_exporter.py      # openpyxl writer with custom formatting
    ├── loaders/                   # Ingestion modules
    │   ├── __init__.py
    │   ├── base_loader.py         # Parsing and downcasting mechanics
    │   ├── closing_stock_loader.py
    │   ├── grn_loader.py
    │   ├── pov_loader.py
    │   └── pv_loader.py
    └── processors/                # Data processors
        ├── __init__.py
        ├── anomaly_extractor.py   # Relational anti-join exception engine
        ├── data_cleaner.py        # Cleans and sanitizes strings for export
        ├── demand_aggregator.py   # Aggregates consumption metrics
        ├── item_linker.py         # POV to GRN document matcher
        ├── lead_time_calculator.py# Lead time descriptive statistics
        ├── lead_time_predictor.py # Random Forest model for lead times
        ├── supplier_aggregator.py # Prepares vendor operational feature matrices
        ├── time_series_trainer.py # Training coordinator for autoregressive models
        └── similarity/            # Similarity detection strategies
            ├── __init__.py
            ├── base_similarity.py
            ├── semantic_similarity.py # SBERT semantic encoder
            └── tfidf_similarity.py    # Sparse character-level distances


8. Output Inventory Reports

The system outputs a formatted, multi-sheet Excel workbook (.xlsx) using openpyxl. Top rows are frozen, filters are applied automatically, and columns are adjusted to prevent text truncation.

Sheet Name

Contents

Formatting & Rules

Summary

High-level execution metadata, including total item counts, categorized ABC volumes, and run times.

Unfiltered layout. Includes written instructions for adding Closing Stock data.

ABC Classification

Sorted list of inventory items with cumulative cost contributions and assigned ABC categories.

Auto-filters enabled. Features alternating row colors based on ABC class.

Monthly Forecast

Active monthly reorder quantities, indicating the selected algorithm and MAPE scores.

Quantities highlighted in bold. Includes conditional formatting.

Quarterly Forecast

Active quarterly reorder quantities, indicating the selected algorithm and MAPE scores.

Quantities highlighted in bold. Includes conditional formatting.

Delivery Exceptions

Orphaned documents isolated using relational anti-joins (e.g., Pending POs or Unordered Receipts).

Features distinct categorizations for missing document types.

Supplier Risk Report

Vendor risk tiers categorized by the risk engine.

Styled with red (High), yellow (Medium), and green (Low) background fills.

Monthly Breakdown

Historical quantities purchased per calendar month, formatted as an interactive pivot table.

Formatted with Indian digit separations (e.g., 1,00,000).

Lead Times

Descriptive lead time metrics (Min, Median, Max) calculated per item-supplier pair.

Unreliable statistics (less than 3 observations) are flagged.

Anomaly Report

Transaction outliers identified by the Isolation Forest engine.

Displays anomaly severity and raw isolation scores.

Raw GRN

Cleaned and validated raw Goods Received Note records.

Formula sanitization applied.

Raw POV

Cleaned and validated raw Purchase Order Voucher records.

Formula sanitization applied.

Raw PV

Cleaned and validated raw final Purchase Voucher records.

Formula sanitization applied.

9. Logging & Diagnostics

Location: logs/app.log, resolved dynamically relative to the project root.

Rotation: Configured with RotatingFileHandler (max size: 5 MB, keeping 3 historical backups).

Log Level Separation:

Console handler outputs high-level operations at the INFO level.

File handler records detailed analytical operations at the DEBUG level.

Format: [YYYY-MM-DD HH:MM:SS] [LEVEL] [module] — message.

10. Installation & Local Setup

The system uses uv for lightning-fast, reproducible package management.

Prerequisites

Ensure Python 3.10 or higher is installed. To check, run:

python --version


Installation Steps

Clone the Repository:

git clone [https://github.com/your-org/procurement-analytics.git](https://github.com/your-org/procurement-analytics.git)
cd procurement-analytics


Initialize the Environment:
Create a localized virtual environment and install all pinned dependencies using uv:

uv venv
# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Sync dependencies
uv pip install -r requirements.txt


Generate Required Directories:
Create target directory pathways for raw data, models, logs, and outputs:

mkdir -p data/grn data/purchase_orders data/purchase_vouchers data/closing_stock output logs models


11. Execution Guides

Graphical User Interface Mode

To run the full PyQt6 graphical workspace:

python run_gui.py


Step-by-Step UI Workflow:

File Setup: Use the picker widgets to select paths for POV, GRN, and PV CSV exports.

Configure Output: Select the output directory and specify the report filename. Enter the expected annual growth percentage (defaults to $30.0\%$).

Model Training (Optional): Open the "Model Training" tab and click "Execute XGBoost Training Sequence". This fits autoregressive XGBoost models to your historical data, validating accuracy and saving superior estimators to the models/ directory.

Run Analysis: Return to "Configure Output" and check "Enable ML Time-Series Forecasting". Click "Run Analysis" to start the pipeline. The progress bar will pulse as execution runs on a background thread.

View Results: On completion, the results view displays dynamic KPI cards, an interactive Pareto chart, and an editable data preview table. Click "Open Output File" to view the generated Excel sheet in your system's default viewer.