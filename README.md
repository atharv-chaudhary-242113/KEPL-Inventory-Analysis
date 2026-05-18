# KEPL Procurement Analytics & Inventory Forecasting System

A procurement analytics desktop application custom-built for **Khokhar Electricals Pvt. Ltd. (KEPL)**. The system ingests transactional CSV exports from Tally — Purchase Order Vouchers (POV), Goods Received Notes (GRN), and Purchase Vouchers (PV) — and produces a formatted multi-sheet Excel workbook containing ABC classification, demand forecasts, supplier risk profiles, anomaly flags, and lead time analytics.

---

## Features

- **ABC Inventory Classification** — Pareto-based stratification of items by cumulative consumption value, with configurable A/B thresholds.
- **Dynamic Ensemble Demand Forecasting** — Per-item MAPE-driven selection between XGBoost autoregressive models and Holt-Winters triple exponential smoothing, with a growth-scaled baseline fallback.
- **Supplier Risk Segmentation** — K-Means clustering on vendor performance vectors (spend, lead time, delivery volatility), with a quantile-scoring deterministic fallback.
- **Procurement Anomaly Detection** — Isolation Forest on purchase voucher transactions to flag outlier price/quantity records.
- **Document Exception Reporting** — Anti-join logic across POV and GRN datasets to surface orphaned or unmatched procurement documents.
- **Semantic Entity Deduplication** — SBERT (all-MiniLM-L6-v2) embeddings to flag near-duplicate supplier/item names at a configurable cosine similarity threshold (default: 0.85).
- **PyQt6 Desktop GUI** — Non-blocking QThread execution with real-time log output, an embedded Pareto chart, and a tabular results preview.
- **Low-Memory Mode** — Configurable lite mode that reduces batch sizes and enforces explicit garbage collection for 4 GB RAM environments.

---

## Tech Stack

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.12.x | Runtime (exact series required) |
| pandas | ≥ 2.0 | Data ingestion and transformation |
| numpy | ≥ 1.24 | Numerical operations |
| scikit-learn | ≥ 1.3 | K-Means, Isolation Forest, RobustScaler |
| xgboost | ≥ 2.0 | Autoregressive demand forecasting |
| statsmodels | 0.14.6 | Holt-Winters exponential smoothing |
| sentence-transformers | ≥ 2.2 | Semantic entity deduplication |
| torch | ≥ 2.0 | SBERT model backend |
| PyQt6 | 6.6.1 (pinned) | Desktop GUI |
| openpyxl | ≥ 3.1 | Excel workbook generation |
| matplotlib | ≥ 3.7 | Embedded Pareto chart |

> **Package manager:** The project uses [`uv`](https://github.com/astral-sh/uv). A `requirements.txt` is also provided for compatibility.

---

## Directory Structure

```
KEPL-Inventory-Analysis/
├── run_gui.py                      # Entry point — launches PyQt6 application
├── pyproject.toml                  # uv project definition and pinned dependencies
├── requirements.txt                # pip-compatible dependency list
├── .gitignore
├── gui/                            # PyQt6 user interface package
│   ├── app.py                      # QMainWindow bootstrap
│   ├── views/
│   │   ├── main_window.py          # App shell — navigation, layout, sidebars
│   │   ├── file_selection_view.py  # File picker panel (POV, GRN, PV inputs)
│   │   ├── output_config_view.py   # Run configuration and output path panel
│   │   ├── ml_training_view.py     # XGBoost model training controller
│   │   ├── log_view.py             # Real-time scrolling diagnostic log terminal
│   │   └── results_view.py         # KPI cards, Pareto chart, data preview table
│   └── widgets/
│       ├── abc_chart_widget.py     # Embedded Matplotlib canvas
│       ├── file_picker.py          # File selection component
│       └── folder_picker.py        # Directory selection component
└── src/                            # Core analytics engine
    ├── pipeline.py                 # Central orchestration controller
    ├── logger_config.py            # Logging setup with RotatingFileHandler
    ├── loaders/                    # Tally CSV ingestion modules
    │   ├── base_loader.py          # Abstract loader with file size validation (5 MB cap)
    │   ├── pov_loader.py
    │   ├── grn_loader.py
    │   ├── pv_loader.py
    │   └── closing_stock_loader.py
    ├── processors/                 # Data transformation modules
    │   ├── data_cleaner.py         # Forward-fill, normalisation, export sanitisation
    │   ├── item_linker.py          # POV→GRN document matching via date-window join
    │   ├── lead_time_calculator.py # Lead time descriptive statistics
    │   ├── lead_time_predictor.py  # Random Forest lead time predictor
    │   ├── demand_aggregator.py    # Monthly consumption aggregation
    │   ├── supplier_aggregator.py  # Vendor performance feature matrix builder
    │   ├── anomaly_extractor.py    # Anti-join exception engine
    │   └── similarity/
    │       ├── base_similarity.py
    │       ├── semantic_similarity.py  # SBERT encoder (all-MiniLM-L6-v2)
    │       └── tfidf_similarity.py     # TF-IDF character-level fallback
    ├── analysis/                   # Analytical and forecasting strategies
    │   ├── abc_classifier.py
    │   ├── anomaly_detector.py     # Isolation Forest on PV transactions
    │   ├── base_forecast_strategy.py
    │   ├── simple_forecast.py      # Growth-scaled baseline (default: 1.30×)
    │   ├── holt_winters_forecast.py
    │   ├── xgboost_forecast.py
    │   ├── ensemble_forecast.py    # MAPE-driven dynamic strategy selector
    │   ├── stock_adjusted_forecast.py
    │   └── supplier_risk_segmenter.py
    ├── exporters/
    │   ├── base_exporter.py
    │   └── excel_exporter.py       # openpyxl multi-sheet workbook writer
    └── time_series_trainer.py      # XGBoost training coordinator
```

> **Note:** `data/`, `logs/`, `output/`, and `models/` are excluded from version control via `.gitignore`. You must create them locally (see Installation).

---

## Installation

### Prerequisites

Python **3.12.x** is required exactly.

```bash
python --version   # Should output Python 3.12.x
```

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/atharv-chaudhary-242113/KEPL-Inventory-Analysis.git
cd KEPL-Inventory-Analysis
```

**2. Create and activate a virtual environment**

Using `uv` (recommended):
```bash
uv venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Using standard `venv`:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

Using `uv`:
```bash
uv pip install -r requirements.txt
```

Using `pip`:
```bash
pip install -r requirements.txt
```

**4. Create required local directories**

```bash
mkdir -p data/grn data/purchase_orders data/purchase_vouchers data/closing_stock output logs models
```

---

## Running the Application

```bash
python run_gui.py
```

The application opens maximized with the Qt Fusion theme applied.

---

## Usage Workflow

### Step 1 — Select Input Files

On the **File Setup** tab, use the file picker widgets to select your Tally CSV exports:
- **POV** — Purchase Order Vouchers
- **GRN** — Goods Received Notes
- **PV** — Purchase Vouchers

Optionally provide a **Closing Stock** file. If supplied, the pipeline uses `StockAdjustedForecastStrategy` (net demand = gross forecast − closing stock) instead of the simple baseline.

### Step 2 — Configure Output

On the **Configure Output** tab:
- Select the output directory and specify the report filename.
- Set the expected **annual growth rate** (default: `1.30`, i.e. 30% growth applied to baseline forecasts).
- Optionally enable **ML Time-Series Forecasting** to include XGBoost and Holt-Winters models in the ensemble.

### Step 3 — Train ML Models (Optional)

Open the **Model Training** tab and click **Execute XGBoost Training Sequence**. This fits per-item autoregressive XGBoost regressors on historical PV data and serialises the best-performing models to `models/` as `.joblib` files. Models are only used if ML forecasting is enabled in Step 2.

### Step 4 — Run Analysis

Click **Run Analysis**. The pipeline executes on a background `QThread` — the UI remains fully responsive and the log terminal streams real-time diagnostics.

### Step 5 — View Results

On completion, the **Results** view displays:
- KPI summary cards (item counts by ABC class, execution time)
- Interactive Pareto chart
- Tabular data preview

Click **Open Output File** to open the generated Excel report.

---

## Pipeline Configuration Reference

These keys are accepted by `AnalysisPipeline` via its `config` dict. The GUI populates all of them; this table is useful if you integrate the pipeline programmatically.

| Key | Type | Default | Description |
|---|---|---|---|
| `pov_path` | `str` | **required** | Path to POV CSV export |
| `grn_path` | `str` | **required** | Path to GRN CSV export |
| `pv_path` | `str` | **required** | Path to PV CSV export |
| `output_path` | `str` | `None` | Output Excel file path. If omitted, export is skipped. |
| `closing_stock_path` | `str` | `None` | Optional closing stock CSV |
| `closing_stock_freq` | `str` | `'monthly'` | Frequency of closing stock data |
| `is_lite_mode` | `bool` | `True` | Enables low-memory mode (batch size 1,000 vs 10,000 and explicit GC) |
| `growth_rate` | `float` | `1.30` | Annual growth multiplier applied by the baseline forecast strategy |
| `abc_threshold_a` | `float` | `70.0` | Cumulative % cutoff for Class A items |
| `abc_threshold_b` | `float` | `90.0` | Cumulative % cutoff for Class B items |
| `lead_time_day_window` | `int` | `14` | Maximum days between POV and GRN to consider a valid link |
| `models_dir` | `str` | `'models'` | Directory containing serialised XGBoost `.joblib` model files |
| `holt_winters_seasonal_periods` | `int` | `12` | Seasonal cycle length for Holt-Winters (12 = annual) |
| `holt_winters_trend` | `str` | `'add'` | Trend component type: `'add'` or `'mul'` |
| `holt_winters_seasonal` | `str` | `'add'` | Seasonal component type: `'add'` or `'mul'` |

---

## Input Data Format

All three source files must be Tally multi-line voucher CSV exports. The loaders skip the first 6 rows of Tally metadata and treat row 7 as the header. Required columns per file type:

| File | Required Columns |
|---|---|
| POV | `Date`, `Vch/Bill No`, `Particulars`, `Item Details`, `Qty.`, `Price`, `Amount`, `Unit` |
| GRN | `Date`, `Vch/Bill No`, `Particulars`, `Item Details`, `Qty.`, `Unit` |
| PV | `Date`, `Vch/Bill No`, `Particulars`, `Item Details`, `Qty.`, `Price`, `Amount`, `Unit` |

**Preprocessing applied automatically by `DataCleaner`:**
- Forward-fills `Date`, `Vch/Bill No`, and `Particulars` within voucher blocks (Tally only populates these on the first line item of each voucher).
- Strips rows where `Unit == '-'` and rows matching `freight|tax|charge` in `Item Details`.
- Lowercases and strips whitespace from `Item Details` and `Particulars`.
- Prepends a `'` to any cell value starting with `=`, `+`, `-`, or `@` before export (CSV injection prevention).
- **File size limit:** 5 MB per input file, enforced by the base loader. Export a narrower date range from Tally if your file exceeds this.

---

## Output Report Sheets

The generated `.xlsx` workbook contains the following sheets:

| Sheet | Contents |
|---|---|
| **Summary** | Execution metadata: date range, total items processed, counts per ABC class, and run duration. No autofilter. |
| **ABC Classification** | Full item list with cumulative cost percentages and assigned A/B/C class. Autofilter enabled. |
| **Monthly Forecast** | Per-item monthly reorder quantities with the winning algorithm name and its backtest MAPE. |
| **Quarterly Forecast** | Per-item quarterly reorder quantities with algorithm and MAPE columns. |
| **Delivery Exceptions** | Orphaned documents identified by anti-join across POV and GRN (e.g. purchase orders with no matching receipt). |
| **Supplier Risk Report** | Vendor risk tiers (High / Medium / Low) with colour-coded rows — red, yellow, and green fills respectively. |
| **Lead Times** | Min, median, and max lead time in days per item–supplier pair. |
| **Raw GRN** | Cleaned GRN records with formula-injection sanitisation applied. |
| **Raw POV** | Cleaned POV records with sanitisation applied. |
| **Raw PV** | Cleaned PV records with sanitisation applied. |

All sheets except Summary have column autofit and header autofilter applied.

---

## Forecasting Logic

The `DynamicEnsembleForecastStrategy` runs all three models independently for every item, then selects the winner **per row** based on backtest MAPE:

1. If both XGBoost and Holt-Winters produce a valid numeric MAPE, the lower-MAPE model wins.
2. If only one model produces a valid MAPE, that model is used.
3. If neither model produces a valid MAPE (e.g. insufficient history, missing `.joblib` file), the baseline fallback is used.

The result column `Forecast_Algorithm` is prefixed with `"Ensemble: "` followed by the winning model's name. Holt-Winters requires at least 24 months of historical data (two full seasonal periods of 12).

---

## Logging

- **Location:** `logs/app.log` (resolved relative to project root)
- **Rotation:** `RotatingFileHandler` — max 5 MB per file, 3 backup files retained
- **Console:** `INFO` level and above
- **File:** `DEBUG` level and above
- **Format:** `[YYYY-MM-DD HH:MM:SS] [LEVEL] [module] — message`