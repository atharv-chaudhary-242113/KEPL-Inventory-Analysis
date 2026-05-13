# KEPL-Inventory-Analysis
---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Understanding the Data](#2-understanding-the-data)
3. [Methodology](#3-methodology)
4. [Project Architecture & SOLID Principles](#4-project-architecture--solid-principles)
5. [Directory Structure](#5-directory-structure)
6. [File-by-File Description](#6-file-by-file-description)
7. [ABC Classification Logic](#7-abc-classification-logic)
8. [Monthly & Quarterly Forecasting Logic](#8-monthly--quarterly-forecasting-logic)
9. [Closing Stock Dataset (Future Integration)](#9-closing-stock-dataset-future-integration)
10. [GUI Description](#10-gui-description)
11. [CLI (Headless) Mode](#11-cli-headless-mode)
12. [Output Files](#12-output-files)
13. [Logging](#13-logging)
14. [Installation & Setup](#14-installation--setup)
15. [Running the Project](#15-running-the-project)
16. [.gitignore](#16-gitignore)
17. [Dependencies](#17-dependencies)
18. [Future Improvements](#18-future-improvements)

---

## 1. Project Overview

This project is a **Procurement Analytics and Inventory Forecasting System** for Khokhar Electricals Pvt. Ltd. It ingests three types of procurement documents — **Purchase Order Vouchers (POV)**, **Goods Received Notes (GRN)**, and **Purchase Vouchers (PV)** — and produces:

- **ABC Category Classification** of all procured items, based on consumption value.
- **Monthly and Quarterly Reorder Quantity Estimates** per item, so that stock ordered once in a period does not need to be reordered within the same period.
- An **Excel output report** the user can save anywhere on their machine.
- A **clean GUI** that any non-technical user can operate after a one-time setup.

The system is designed to be **extended easily** — most notably when a Closing Stock dataset becomes available — without rewriting any existing logic.

---

## 2. Understanding the Data

### Common Structure (All Three Files)

All three CSV files are exported from a Tally-style accounting software. They share this format:

```
Rows 0–4  : Company header metadata (company name, address, report type, date range, notes)
Row 5     : (blank)
Row 6     : Actual column headers → Date | Vch/Bill No | Particulars | Item Details | Material Centre | Qty. | Unit | Price | Amount | Notes
Row 7+    : Data rows
```

**Columns (after parsing):**

| Column | Description |
|---|---|
| `Date` | Voucher date (DD-MM-YYYY). Present only on the **first item row** of each voucher; subsequent item rows of the same voucher have this blank — it must be forward-filled. |
| `Vch/Bill No` | Unique voucher number. Same forward-fill rule applies. |
| `Particulars` | Vendor/Party name. Same forward-fill rule applies. |
| `Item Details` | Name of the item/product. Present on every item row. |
| `Material Centre` | Warehouse/branch where the item is received/ordered. |
| `Qty.` | Quantity in the transaction. |
| `Unit` | Unit of measurement (Nos, Mtr, Kg, etc.). |
| `Price` | Unit price. |
| `Amount` | Total = Qty. × Price. |
| `Notes` | Optional internal notes. |

> **Key Parsing Challenge:** Each voucher may span multiple rows (one row per line item). Only the first item row of each voucher carries the `Date`, `Vch/Bill No`, and `Particulars` — the rest are blank until the next voucher starts. The parser must **forward-fill** these three columns within each file.

### Item Identity Rule

An item is uniquely identified by the composite key:
```
(Item Details, Particulars, Date)
```
- **`Item Details`** is the product name.
- **`Particulars`** is the supplier/party name.
- **`Date`** is the date of the voucher.

This means: "Item X from Supplier Y on Date Z" is a single traceable procurement event.

### Lead Time

Purchase Order Vouchers are placed first. The same item appears in GRN after a **delivery lag** (typically days to weeks). The system does not assume a fixed lead time — instead it **computes the observed lead time** empirically: for each `(Item Details, Particulars)` pair, it finds matching events between POV and GRN and calculates the average/median day difference.

### Split Deliveries

A single POV line item (e.g., 60 units of Item A from Supplier Z) may arrive as multiple GRN entries across different dates (e.g., 1 unit on Day 10, 59 units on Day 12). The system accumulates all GRN quantities linked to a POV line item before computing fulfilment.

---

## 3. Methodology

### Step 1 — Parse & Clean
- Skip header metadata rows.
- Apply column headers from row 6.
- Forward-fill `Date`, `Vch/Bill No`, `Particulars` within each voucher block.
- Parse `Date` to `datetime`.
- Cast `Qty.`, `Price`, `Amount` to numeric (coerce errors to NaN, then drop or flag).
- Reject any input file exceeding 5 MB before loading — a clear error is raised with the actual file size and a suggestion to export a smaller date range from Tally.
- Filter out non-item rows (e.g., "Freight Charges", rows with `-` in Unit, rows where `Item Details` contains tax/freight keywords).
- Normalise `Item Details` and `Particulars` by stripping whitespace and applying `.str.lower()` to eliminate case-sensitive duplicate grouping.
- Flag similar item names using TF-IDF + cosine similarity (character n-grams, threshold 0.85, validated to be between 0.5 and 1.0) — logs warnings for likely duplicates, no auto-merge.
- Flag similar supplier names using the same TF-IDF method.
- Sanitise all string cell values before Excel export — strings beginning with `=`, `+`, `-`, or `@` are prefixed with a single quote on a **copy** of the DataFrame, so the original data shown in the GUI remains unaffected.
- Resolve the log directory path relative to the project root using `Path(__file__).resolve()` — not the current working directory.

### Step 2 — Normalise & Link
- Build a unified item-level dataframe from PV (the most reliable consumption signal, since it records what was actually billed/paid).
- Enrich with GRN data (actual receipt quantities and dates).
- Use POV for lead time computation and to flag orders that haven't been received yet.

### Step 3 — ABC Analysis
- Compute **annual consumption value** per item = `total Qty received × average unit Price` (from PV data).
- Sort items in descending order of consumption value.
- Compute cumulative % of total value.
- Classify:
  - **A** → top items accounting for 0–70% of cumulative value.
  - **B** → next items accounting for 70–90% of cumulative value.
  - **C** → remaining items accounting for 90–100% of cumulative value.

### Step 4 — Demand Estimation
Since there is no historical closing stock data yet, demand is estimated purely from consumption:
- **Monthly demand** = total quantity purchased (PV) in the date range ÷ number of months covered.
- **Quarterly demand** = monthly demand × 3.
- These are straight averages; once closing stock data arrives, they will be upgraded to account for opening/closing inventory.

### Step 5 — Reorder Quantity Recommendation
- **Monthly reorder qty** = ceil(monthly average demand) — this is the qty to order once at the start of a month so no reorder is needed within the month.
- **Quarterly reorder qty** = ceil(quarterly average demand).
- Both are computed per `(Item Details, Particulars, Unit)` triplet so the supplier context is preserved.

---

## 4. Project Architecture & SOLID Principles

This project follows **SOLID** principles with special emphasis on **KISS** (Keep It Simple, Stupid) and **OCP** (Open/Closed Principle):

| Principle | How It Applies |
|---|---|
| **S** — Single Responsibility | Each class/module does exactly one job. `DataParser` only parses. `ABCClassifier` only classifies. `ForecastEngine` only forecasts. The GUI only handles user interaction. |
| **O** — Open/Closed | New dataset types (e.g., Closing Stock) are added by writing a **new loader class** that conforms to the `BaseLoader` interface — no existing loader is modified. Similarly, new analysis strategies (e.g., EOQ when cost data is available) are added as new strategy classes. |
| **L** — Liskov Substitution | All loaders are interchangeable through the `BaseLoader` abstract class. |
| **I** — Interface Segregation | The GUI consumes `AnalysisPipeline` through a thin, purpose-specific interface. |
| **D** — Dependency Inversion | High-level modules (`AnalysisPipeline`) depend on abstractions, not concrete implementations. |

**KISS** is enforced by avoiding unnecessary abstraction layers. There are no factories-of-factories. Every class has a clear, plain-English purpose.

**OCP** is the most important principle here: the closing stock integration point is **already designed as an open extension slot** from day one — a `ClosingStockLoader` class and a `StockAdjustedForecastStrategy` class can be dropped in without touching any existing code.

---

## 5. Directory Structure

```
procurement-analytics/
│
├── data/                          # ← (gitignored) User-supplied raw data files
│   ├── grn/
│   ├── purchase_orders/
│   ├── purchase_vouchers/
│   └── closing_stock/             # ← reserved for future dataset
│
├── output/                        # ← (gitignored) Generated reports land here by default
│
├── models/                        # ← (gitignored) Persisted ML models
│   └── lead_time_predictor.joblib # Saved after each successful training run
│
├── logs/                          # ← Application logs
│   └── app.log
│
├── src/                           # ← All source code
│   │
│   ├── loaders/                   # Data ingestion layer
│   │   ├── __init__.py
│   │   ├── base_loader.py         # Abstract base class for all loaders
│   │   ├── grn_loader.py          # Loads & cleans GRN.csv
│   │   ├── pov_loader.py          # Loads & cleans Purchase_Order_Vouchers.csv
│   │   ├── pv_loader.py           # Loads & cleans Purchase_Vouchers.csv
│   │   └── closing_stock_loader.py # STUB — ready for future dataset (daily/weekly/monthly/quarterly)
│   │
│   ├── processors/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── data_cleaner.py        # Forward-fill, type casting, row filtering, deduplication flagging
│   │   ├── item_linker.py         # Links POV → GRN → PV by (Item, Supplier, approximate date)
│   │   ├── lead_time_calculator.py# Computes empirical lead time per (Item, Supplier)
│   │   ├── lead_time_predictor.py # RandomForest-based lead time prediction with joblib persistence
│   │   └── demand_aggregator.py   # Aggregates qty by item, month, quarter
│   │
│   ├── analysis/                  # Analysis layer
│   │   ├── __init__.py
│   │   ├── abc_classifier.py      # ABC classification logic
│   │   ├── anomaly_detector.py    # IsolationForest-based procurement anomaly detection
│   │   ├── base_forecast_strategy.py  # Abstract forecast strategy (OCP hook)
│   │   ├── simple_forecast.py     # Avg-based monthly & quarterly forecast (no stock data)
│   │   └── stock_adjusted_forecast.py # STUB — activates when closing stock data is present
│   │
│   ├── exporters/                 # Output layer
│   │   ├── __init__.py
│   │   ├── base_exporter.py       # Abstract exporter
│   │   └── excel_exporter.py      # Writes multi-sheet Excel report
│   │
│   ├── pipeline.py                # Orchestrates all steps end-to-end
│   └── logger_config.py           # Centralised logging setup
│
├── gui/                           # GUI layer (completely separate from src/)
│   ├── __init__.py
│   ├── app.py                     # Main GUI entry point (tkinter)
│   ├── views/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Root window, layout, navigation sidebar
│   │   ├── file_selection_view.py # File browser panels for each dataset type
│   │   ├── output_config_view.py  # Output folder browser + run button
│   │   ├── results_view.py        # Displays summary tables & ABC chart after run
│   │   └── log_view.py            # Live log tail panel inside the GUI
│   └── widgets/
│       ├── __init__.py
│       ├── file_picker.py         # Reusable "Browse…" widget for a single file
│       ├── folder_picker.py       # Reusable "Browse…" widget for output folder
│       ├── status_bar.py          # Bottom status bar showing current operation
│       └── abc_chart_widget.py    # Embedded matplotlib Pareto chart
│
├── run_gui.py                     # GUI entry point — launches the tkinter app
├── requirements.txt               # All dependencies pinned
├── .gitignore
└── README.md
```

---

## 6. File-by-File Description

### Root Level

**`run_gui.py`**
The GUI entry point. Imports and launches `gui/app.py`. No logic here — its sole job is to start the GUI event loop.

**`requirements.txt`**
Pinned dependency list (see §17).

**`.gitignore`**
Described fully in §16.

---

### `src/loaders/`

**`base_loader.py`**
Defines `BaseLoader`, an abstract class with one mandatory method: `load(filepath: str) -> pd.DataFrame`. All concrete loaders inherit from this. This is the OCP hook — adding a new document type means writing a new class, not modifying existing ones.

**`grn_loader.py`** — `class GRNLoader(BaseLoader)`
- Checks the file size before loading — raises a `ValueError` with a clear message if the file exceeds 5 MB (5 × 1024 × 1024 bytes), including the actual file size and a suggestion to export a smaller date range from Tally.
- Reads the CSV, skips rows 0–5 (metadata), uses row 6 as header.
- Forward-fills `Date`, `Vch/Bill No`, `Particulars`.
- Parses `Date` as `datetime`.
- Casts `Qty.`, `Price`, `Amount` to float.
- Filters out freight/tax rows (where `Unit == '-'` or `Item Details` matches known non-item patterns like "Freight Charges").
- Logs only the filename (not the full path) at DEBUG level.
- Returns a clean DataFrame with consistent column names.

**`pov_loader.py`** — `class POVLoader(BaseLoader)`
Identical structure to GRNLoader, including the 5 MB file size check, but for Purchase Order Vouchers. The voucher number prefix will be `PO/...`.

**`pv_loader.py`** — `class PVLoader(BaseLoader)`
Identical structure, including the 5 MB file size check, but for Purchase Vouchers.

**`closing_stock_loader.py`** — `class ClosingStockLoader(BaseLoader)`
A **stub** that is already wired into the pipeline but returns `None` when no file is provided. When the dataset arrives, only this file needs to be filled in. Handles four sub-formats selectable by the user: `daily`, `weekly`, `monthly`, `quarterly`. Each sub-format normalises the data into the same output schema: `(Item Details, Particulars, Period, Closing Qty)`.

---

### `src/processors/`

**`data_cleaner.py`** — `class DataCleaner`
A stateless utility (all static methods). Responsibilities:
- `forward_fill_voucher_fields(df)`: fills down `Date`, `Vch/Bill No`, `Particulars` within each file.
- `cast_numeric_columns(df)`: casts quantity/price/amount columns to float with `errors='coerce'`.
- `drop_non_item_rows(df)`: removes rows identified as freight, tax, or summary rows.
- `normalise_item_names(df)`: strips leading/trailing whitespace from `Item Details` and `Particulars` and applies `.str.lower()` to both — eliminating case-sensitive duplicate grouping.
- `flag_similar_item_names(df, threshold=0.85)`: validates that `threshold` is between 0.5 and 1.0 (raises `ValueError` otherwise), then uses TF-IDF vectorisation with character n-grams (range 2–4) and cosine similarity to detect near-duplicate item names. Logs warnings only — does not modify data. Human review required before any merge.
- `flag_similar_supplier_names(df, threshold=0.85)`: same validation and logic applied to `Particulars` (supplier names).
- `sanitise_for_export(df)`: creates a copy of the DataFrame (`df.copy()`) at the start, then iterates all string columns on the copy and prepends `'` to any value beginning with `=`, `+`, `-`, or `@`, preventing Excel formula injection. Returns the sanitised copy — the original DataFrame passed in is never mutated, so the GUI's in-memory data remains unaffected.

**`item_linker.py`** — `class ItemLinker`
Responsible for creating a unified view of `(Item Details, Particulars)` across all three datasets. It does a **fuzzy date-windowed join**: for each POV entry, it looks for matching GRN and PV entries within a configurable day window (default: ±14 days) with the same `Item Details` and `Particulars`. An additional **quantity proximity check** ensures only GRN entries whose quantity falls within 2× of the POV quantity are linked, preventing cross-linking of genuinely separate orders that fall within the date window. This handles split deliveries naturally — multiple GRN rows matching one POV row are aggregated. Returns a linked DataFrame with columns from all three sources side by side, plus a `lead_time_days` column.

**`lead_time_calculator.py`** — `class LeadTimeCalculator`
Takes the output of `ItemLinker` and computes, per `(Item Details, Particulars)`:
- `avg_lead_time_days`
- `median_lead_time_days`
- `min_lead_time_days`
- `max_lead_time_days`

Logs a `WARNING` for any item-supplier pair with fewer than 3 matched observations, as averages computed from very few samples are unreliable. These feed into the `LeadTimePredictor` model and will also feed into safety stock calculations when closing stock data is available.

**`lead_time_predictor.py`** — `class LeadTimePredictor`
Trains a `RandomForestRegressor(random_state=42)` on historical POV→GRN matched records, ensuring fully reproducible predictions across runs. Features used: `item_encoded`, `supplier_encoded`, `order_qty`, `month_of_year`. Target: `actual_lead_time_days`.

Falls back to the empirical average from `LeadTimeCalculator` under two conditions:
- Fewer than 30 training samples exist for a given item-supplier pair.
- After an 80/20 train/test split, the model's Mean Absolute Error is not lower than the MAE of simply predicting the empirical average for every row — in which case the model is discarded and a `WARNING` is logged.

After a successful training run that passes the quality check, the fitted model is persisted to `models/lead_time_predictor.joblib` using `joblib.dump`. On subsequent runs, if this file exists, the model is loaded from disk instead of retraining, reducing run time as the dataset grows. The persisted model is gitignored.

Exposes `predict(item, supplier, qty, month) -> float`.

**`demand_aggregator.py`** — `class DemandAggregator`
Takes the cleaned PV DataFrame (the final billing record, most reliable for actual consumption). Groups by `(Item Details, Particulars, Unit)`. Computes:
- `total_qty`: total quantity purchased across the full date range.
- `total_value`: total spend (sum of `Amount`).
- `avg_unit_price`: weighted average unit price.
- `months_covered`: number of distinct calendar months present in the data (computed via `df['Date'].dt.to_period('M').nunique()`).
- `avg_monthly_qty`: `total_qty / months_covered`.
- `avg_quarterly_qty`: `avg_monthly_qty × 3`.
- `month_year` column for time-series breakdown.

Logs a `WARNING` for any item where `avg_monthly_qty` computes to `0` after filtering, indicating all rows were dropped and the reorder recommendation will be zero — prompting the user to check the source data.

---

### `src/analysis/`

**`base_forecast_strategy.py`** — `class BaseForecastStrategy` (abstract)
Defines the interface: `compute(aggregated_df: pd.DataFrame, closing_stock_df: pd.DataFrame | None) -> pd.DataFrame`. The `closing_stock_df` parameter defaults to `None`, so all existing callers remain unaffected when closing stock is not yet available.

**`abc_classifier.py`** — `class ABCClassifier`
- Takes the output of `DemandAggregator` (which includes `total_value` per item).
- Sorts by `total_value` descending.
- Computes cumulative value percentage.
- Assigns `abc_class`: `'A'` (0–70%), `'B'` (70–90%), `'C'` (90–100%).
- Returns the DataFrame with an `abc_class` column appended.
- The thresholds (70, 90) are configurable as constructor parameters so they can be adjusted without touching logic.

**`anomaly_detector.py`** — `class AnomalyDetector`
Runs `IsolationForest(contamination='auto', random_state=42)` on all procurement records after cleaning. Using `contamination='auto'` allows the algorithm to determine the anomaly threshold from the data itself, based on the scoring method defined in the original IsolationForest paper — rather than assuming a fixed percentage. `random_state=42` ensures results are reproducible across runs.

Features used: `unit_price`, `qty`, `month_of_year`. The `amount` column is intentionally excluded — since `amount = qty × unit_price`, including it would introduce multicollinearity and skew isolation scores toward amount outliers rather than independently unusual prices or quantities.

`contamination` is a configurable constructor parameter (defaulting to `'auto'`) so it can be overridden if needed without touching any logic. Appends two columns to the DataFrame: `is_anomaly` (boolean) and `anomaly_score` (float — the raw isolation score). Anomalous rows are flagged in the Excel output under the `Anomaly Report` sheet and logged as `WARNING` entries. No records are dropped — flagging only.

**`simple_forecast.py`** — `class SimpleForecastStrategy(BaseForecastStrategy)`
The active strategy when no closing stock data is available.
- `monthly_reorder_qty = ceil(avg_monthly_qty)` — rounded up to avoid stockouts.
- `quarterly_reorder_qty = ceil(avg_quarterly_qty)`.
- Also provides a **monthly breakdown table**: for each item, shows actual qty purchased per calendar month across the dataset range, giving the user visibility into seasonality.

**`stock_adjusted_forecast.py`** — `class StockAdjustedForecastStrategy(BaseForecastStrategy)` — **STUB**
When activated (by passing closing stock data), this strategy will subtract closing stock from gross demand to compute net demand. The formula slot is:
```
net_monthly_demand = gross_monthly_demand - avg_closing_stock
monthly_reorder_qty = ceil(net_monthly_demand)
```
This file exists today but raises `NotImplementedError` with a clear message explaining it requires closing stock data. The pipeline catches this exception, logs a warning, and automatically falls back to `SimpleForecastStrategy` — so no crash occurs if a user accidentally provides a closing stock file before this stub is implemented. It will be filled in when that dataset arrives, with zero changes to the rest of the codebase.

---

### `src/exporters/`

**`base_exporter.py`** — `class BaseExporter` (abstract)
Defines: `export(results: dict, output_path: str) -> None`.

**`excel_exporter.py`** — `class ExcelExporter(BaseExporter)`
Calls `DataCleaner.sanitise_for_export()` on every DataFrame before writing any sheet, preventing formula injection across all output including Raw sheets. The sanitised copy is used for writing only — the original DataFrames in the `results` dict are not modified.

Respects the `include_anomaly_report` flag in the pipeline `config` dict (defaults to `True`). When set to `False`, the `Anomaly Report` sheet is omitted from the output — useful for reports shared externally with vendors or auditors.

Writes a multi-sheet `.xlsx` file using `openpyxl`. Sheets produced:

| Sheet Name | Contents |
|---|---|
| `Summary` | Run metadata: date range of data, files used, items processed, run timestamp |
| `ABC Classification` | Full item list with ABC class, total qty, total value, avg unit price, supplier. Rows flagged by `AnomalyDetector` are highlighted in red with an `Anomaly` column set to `True` and an `Anomaly Score` column showing the raw isolation score. |
| `Monthly Forecast` | Per-item monthly reorder quantity recommendation |
| `Quarterly Forecast` | Per-item quarterly reorder quantity recommendation |
| `Monthly Breakdown` | Actual qty per item per calendar month (pivot table) |
| `Lead Times` | Computed lead time stats per (item, supplier) |
| `Anomaly Report` | All rows flagged as anomalous by IsolationForest, with item, supplier, qty, price, month, and anomaly score. Omitted if `include_anomaly_report` is `False`. |
| `Raw GRN` | Cleaned GRN data — formula injection sanitised |
| `Raw POV` | Cleaned POV data — formula injection sanitised |
| `Raw PV` | Cleaned PV data — formula injection sanitised |

Each sheet has **frozen top row**, **auto-filtered columns**, alternating row colours per ABC class in the ABC sheet, and conditional formatting (green/amber/red) on the reorder quantity columns.

---

### `src/pipeline.py` — `class AnalysisPipeline`

The single orchestrator. Has one public method: `run()`. Internally:

1. Validates all input file paths for existence before starting any processing step — raises a clear error if any required file is missing.
2. Calls each loader (file size validation occurs inside each loader before any data is read).
3. Passes raw DataFrames through `DataCleaner` (including TF-IDF duplicate flagging and export sanitisation).
4. Runs `DemandAggregator` on PV data.
5. Runs `ABCClassifier`.
6. Runs `LeadTimeCalculator` on linked data from `ItemLinker`.
7. Runs `LeadTimePredictor` — loads a persisted model if available, otherwise trains from scratch and saves. Falls back to empirical averages if fewer than 30 samples exist or if the model does not outperform the empirical baseline MAE.
8. Runs `AnomalyDetector` on all cleaned procurement records.
9. Selects the correct forecast strategy (`SimpleForecastStrategy` if no closing stock, else `StockAdjustedForecastStrategy`). Wraps the strategy's `compute()` call in a `try/except NotImplementedError` — if raised, logs a warning and falls back to `SimpleForecastStrategy` automatically.
10. Calls `ExcelExporter`.
11. Returns a `results` dict for the GUI to consume for live display.

The pipeline is instantiated with a `config` dict — file paths, output path, closing stock path (optional), ABC thresholds, and `include_anomaly_report` (boolean, default `True`). This makes it trivially testable and callable from the GUI.

---

### `src/logger_config.py`

Sets up Python's standard `logging` module:
- A **file handler** writing to `logs/app.log` at `DEBUG` level (full detail). The log path is always resolved as an absolute path relative to the project root via `Path(__file__).resolve().parent.parent / 'logs' / 'app.log'` — independent of the working directory the user invokes the script from.
- A **stream/console handler** at `INFO` level.
- Log rotation: `RotatingFileHandler` — max 5 MB per file, keeps 3 backups.
- Format: `[YYYY-MM-DD HH:MM:SS] [LEVEL] [module] — message`.

All other modules import the logger with `logging.getLogger(__name__)` — they never configure handlers themselves.

---

### `gui/app.py`

Builds the root `tkinter.Tk()` window. Sets the window to **full screen at the monitor's native resolution** using `wm_attributes('-fullscreen', True)` (with a non-fullscreen fallback using `winfo_screenwidth()` and `winfo_screenheight()` for platforms where fullscreen is unsupported). Loads and arranges the three main panels: a left navigation sidebar, a main content area (which swaps views), and a bottom status bar. Manages the "current view" state. Starts the `mainloop()`.

---

### `gui/views/`

**`main_window.py`**
Defines the overall window layout using a 3-panel design:
- **Left sidebar** (~200px): Navigation buttons — "File Setup", "Configure Output", "Run & Results", "Logs". Each button switches the main content area.
- **Main content area**: Takes the remaining width. Hosts the swappable view frames.
- **Bottom status bar**: Always visible; shows current operation name and a progress indicator.

Inspired by the clean navigation model of tools like Power BI Desktop and Talend Studio — a dark sidebar with white icon+label buttons, and a clean white/light-grey content area.

**`file_selection_view.py`**
The "File Setup" panel. Contains three independent file picker sections:
- **Purchase Order Vouchers** file picker.
- **GRN** file picker.
- **Purchase Vouchers** file picker.
- **Closing Stock** file picker — marked as **"Optional (future)"** with a subtle badge, and a dropdown to select the data frequency: `Daily / Weekly / Monthly / Quarterly`.

Each picker uses the `FilePicker` widget (see below). The selected paths are stored in `app.py`'s shared config dict.

**`output_config_view.py`**
The "Configure Output" panel. Contains:
- A `FolderPicker` widget to browse the output directory.
- A text entry field for the output filename (defaults to `report_YYYYMMDD.xlsx`).
- A summary of the currently selected input files.
- A prominent **"▶ Run Analysis"** button that triggers `AnalysisPipeline.run()` in a **background thread** (using `threading.Thread` so the GUI doesn't freeze). Results are passed back to the main thread via a `queue.Queue`, checked every 100ms using `after(100, self._check_queue)` — no widget is ever updated directly from the background thread, preventing tkinter thread-safety crashes.

**`results_view.py`**
The "Run & Results" panel. Shown after a successful run. Contains:
- A **summary card** at the top: total items, A items count, B items count, C items count, date range, run duration.
- A **Pareto / ABC bar+line chart** embedded using `matplotlib`'s `FigureCanvasTkAgg` — bars show item value, overlaid line shows cumulative %, with shaded regions for A/B/C zones.
- A **scrollable data table** (`ttk.Treeview`) previewing the top 50 rows of the ABC Classification sheet.
- An **"Open Output File"** button that opens the Excel file in the system's default application.

**`log_view.py`**
The "Logs" panel. A read-only `ScrolledText` widget that tails `logs/app.log` in real time using a polling loop (`after(500, self.refresh)`). Tracks the last-read byte position via `self._log_offset` — only new bytes are read on each poll, keeping performance stable regardless of total log file size. Colour-coded: DEBUG (grey), INFO (black), WARNING (amber), ERROR (red).

---

### `gui/widgets/`

**`file_picker.py`** — `class FilePicker(ttk.Frame)`
A reusable widget containing: a label describing the file type, a read-only entry box showing the current path, and a `Browse…` button that opens `tkinter.filedialog.askopenfilename()` filtered to `.csv` files. Exposes a `get_path()` method and supports an `on_change` callback.

**`folder_picker.py`** — `class FolderPicker(ttk.Frame)`
Same pattern as `FilePicker` but uses `tkinter.filedialog.askdirectory()`. Shows the selected folder path. Exposes `get_path()`.

**`status_bar.py`** — `class StatusBar(ttk.Frame)`
A thin bar docked at the bottom of the window. Has a left-aligned label for status messages and a right-aligned `ttk.Progressbar` in indeterminate mode (pulsing while the pipeline runs, filled/cleared on completion).

**`abc_chart_widget.py`** — `class ABCChartWidget(ttk.Frame)`
Wraps a matplotlib `Figure` and `FigureCanvasTkAgg`. The chart is a dual-axis Pareto chart. Left Y-axis: item consumption value (bar chart). Right Y-axis: cumulative % (line). Background shading: light green (A zone), light yellow (B zone), light red/pink (C zone). The chart auto-resizes with the window.

---

## 7. ABC Classification Logic

ABC Analysis is a form of Pareto analysis applied to inventory:

**Input:** All items from Purchase Vouchers with `total_value = sum(Amount)` per `(Item Details, Particulars)`.

**Algorithm:**
```
1. Sort items by total_value descending.
2. Compute grand_total = sum of all total_values.
3. For each item i (in sorted order):
   cumulative_value_pct[i] = sum(total_value[0..i]) / grand_total × 100
4. Assign class:
   - 'A' if cumulative_value_pct <= 70
   - 'B' if 70 < cumulative_value_pct <= 90
   - 'C' if cumulative_value_pct > 90
```

**Output columns added:**
- `abc_class` — A, B, or C
- `cumulative_value_pct` — running cumulative %
- `value_rank` — integer rank (1 = highest value)

The thresholds `(70, 90)` are passed as constructor arguments to `ABCClassifier`, so they can be changed in config without touching code (OCP).

---

## 8. Monthly & Quarterly Forecasting Logic

### Data Range Detection
The system counts the number of distinct calendar months actually present in the PV dataset:
```
months_covered = df['Date'].dt.to_period('M').nunique()
```
This counts only months that have actual data, eliminating the overcounting problem of arithmetic date-range formulas.

### Per-Item Aggregation
For each `(Item Details, Particulars, Unit)`:
```
total_qty             = sum of Qty. across all PV rows
avg_monthly_qty       = total_qty / months_covered
avg_quarterly_qty     = avg_monthly_qty * 3
monthly_reorder_qty   = ceil(avg_monthly_qty)
quarterly_reorder_qty = ceil(avg_quarterly_qty)
```

`ceil()` ensures you never recommend ordering less than the expected demand.

### Monthly Breakdown Table
A pivot table is also generated showing actual quantities purchased per calendar month per item. This is useful to spot **seasonal demand patterns** — if Item X shows 0 qty in summer and 500 in winter, the flat average is misleading, and the user can manually adjust.

### Caveats Stated in the Output
The Summary sheet will contain a clearly written note:
> "These estimates are based on purchase data only (no closing stock available). If you have historical closing stock data, add it via the Closing Stock file picker to improve accuracy."

---

## 9. Closing Stock Dataset (Future Integration)

The system is **ready** for the closing stock dataset from day one. No re-architecture is needed.

### What Needs to Happen When the Dataset Arrives

1. Open `src/loaders/closing_stock_loader.py` — it already has the class skeleton and four format handlers. Fill in the parsing logic for whichever format the data arrives in.
2. Open `src/analysis/stock_adjusted_forecast.py` — it already has the class skeleton. Implement the `compute()` method:
   ```
   net_monthly_demand = gross_monthly_demand - avg_closing_stock_per_month
   monthly_reorder_qty = ceil(net_monthly_demand)
   ```
3. In `gui/views/file_selection_view.py` — the Closing Stock file picker widget is already there. Just remove the "Optional (future)" badge.

**No other files are touched.** The pipeline already has a conditional check:
```python
if closing_stock_df is not None:
    strategy = StockAdjustedForecastStrategy()
else:
    strategy = SimpleForecastStrategy()
```

### Supported Closing Stock Frequencies
The loader handles all four cases by normalising them to monthly figures:
- **Daily** → group by month, take last day's closing qty as the monthly closing figure.
- **Weekly** → group by month, take the last week's closing qty.
- **Monthly** → used directly.
- **Quarterly** → divide by 3 to get monthly approximation.

---

## 10. GUI Description

### Design Philosophy
The GUI is inspired by analytics tools like **Power BI Desktop** and **Talend Data Integration**: a clean left navigation sidebar on a dark background, a bright main content area, consistent typography, and no cluttered toolbars. The user completes a left-to-right workflow: select files → configure output → run → view results.

### Window Behaviour
- Launches at **full monitor resolution** (uses `winfo_screenwidth()` / `winfo_screenheight()` or fullscreen attribute).
- Fully resizable; all panels use proportional layout (`grid` with `weight` or `pack` with `fill=BOTH, expand=True`).
- File dialogs (Browse) also open at the system's native size.

### Workflow (Step by Step)
```
① Open run_gui.py
     ↓
② "File Setup" tab — Browse for each CSV file individually:
     - Purchase Order Vouchers (.csv)
     - GRN (.csv)
     - Purchase Vouchers (.csv)
     - Closing Stock (.csv) [Optional]
     ↓
③ "Configure Output" tab — Browse output folder, set filename
     ↓
④ Click "▶ Run Analysis"
     - Pipeline runs in background thread
     - Status bar pulses, log panel updates live
     ↓
⑤ "Run & Results" tab appears automatically on success:
     - Summary card
     - Pareto chart
     - Preview table
     - "Open Output File" button
```

### Error Handling in GUI
- If a required file is not selected, the Run button shows a validation error in red before starting.
- If the pipeline throws an exception, a `messagebox.showerror` dialog shows the error, and the full traceback is written to the log.
- All file paths are validated for existence before the pipeline is invoked.
- The pipeline runs in a background thread. All widget updates after completion are marshalled back to the main thread via `queue.Queue` and `after()` polling — preventing tkinter thread-safety crashes.

---

## 11. CLI (Headless) Mode

> **Deferred.** CLI support is planned as a future addition (see §18). The GUI is the only supported entry point at this time.

---

## 12. Output Files

The primary output is a **multi-sheet Excel file** (`.xlsx`). All sheets are documented in §6 under `excel_exporter.py`.

Key formatting details:
- Row 1 of every sheet is frozen and auto-filtered.
- The ABC Classification sheet colour-codes rows: green for A, yellow for B, orange-red for C.
- The Monthly Forecast and Quarterly Forecast sheets include a "Recommended Order Qty" column in bold.
- All numeric columns use the Indian number format (e.g., `1,00,000`) since this is an Indian company.
- The Summary sheet includes a plain-language interpretation of the ABC results.
- All Raw sheets (`Raw GRN`, `Raw POV`, `Raw PV`) have formula injection sanitisation applied before writing — any cell value beginning with `=`, `+`, `-`, or `@` is stored as plain text.
- The `Anomaly Report` sheet is included by default. It can be suppressed by setting `include_anomaly_report: False` in the pipeline config — useful for reports shared externally.

---

## 13. Logging

**Location:** `logs/app.log`, always resolved as an absolute path relative to the project root — the tool can be invoked from any working directory without affecting log output.

**Format:**
```
[2025-04-01 09:15:32] [INFO]  [pipeline] — Starting analysis pipeline
[2025-04-01 09:15:32] [DEBUG] [grn_loader] — Reading file: GRN.csv
[2025-04-01 09:15:33] [INFO]  [grn_loader] — Loaded 22,619 rows after cleaning
[2025-04-01 09:15:33] [WARNING] [data_cleaner] — 47 rows dropped (freight/tax entries)
[2025-04-01 09:15:33] [WARNING] [data_cleaner] — Similar item names detected: 'Copper Wire 4mm' vs 'copper wire 4 mm' [score: 0.923]
[2025-04-01 09:15:33] [WARNING] [demand_aggregator] — Item 'Freight Clip' has avg_monthly_qty=0 after filtering. Reorder qty will be 0.
[2025-04-01 09:15:33] [WARNING] [pipeline] — StockAdjustedForecastStrategy not implemented. Falling back to SimpleForecastStrategy.
[2025-04-01 09:15:33] [WARNING] [lead_time_predictor] — Model MAE (4.2 days) not better than baseline (3.9 days). Falling back to empirical average.
[2025-04-01 09:15:33] [WARNING] [anomaly_detector] — 3 anomalous procurement record(s) flagged. See Anomaly Report sheet.
[2025-04-01 09:15:35] [INFO]  [abc_classifier] — 312 unique items classified: A=28, B=61, C=223
[2025-04-01 09:15:36] [INFO]  [excel_exporter] — Report saved to output/report_20250401.xlsx
[2025-04-01 09:15:36] [INFO]  [pipeline] — Analysis complete in 4.2s
```

**Rotation:** Using `logging.handlers.RotatingFileHandler` — max 5 MB per log file, 3 backups kept (`app.log`, `app.log.1`, `app.log.2`). Old logs are automatically purged.

---

## 14. Installation & Setup

### Prerequisites
- Python **3.10 or higher**
- `pip`
- No database, no internet connection required at runtime.

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/procurement-analytics.git
cd procurement-analytics

# 2. (Recommended) Create a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create required directories (first-time only)
mkdir -p data/grn data/purchase_orders data/purchase_vouchers data/closing_stock output logs models
```

No configuration files need to be edited. The GUI handles all path selection interactively.

---

## 15. Running the Project

### GUI Mode
```bash
python run_gui.py
```
The window opens at full screen. Follow the three-step workflow in the GUI.

---

## 16. .gitignore

```gitignore
# === Data files (never commit raw business data) ===
*.csv
*.xlsx
*.xls
*.ods
*.tsv
data/

# === Output files ===
output/

# === Trained ML models ===
models/

# === Logs ===
logs/
*.log

# === Python environment ===
venv/
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/

# === IDE / editor ===
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# === Testing / coverage ===
.pytest_cache/
.coverage
htmlcov/
```

> **Note:** The three input CSV files, all Excel outputs, and all trained model files are gitignored by default. When sharing the repo, users supply their own data files and models are rebuilt on first run.

---

## 17. Dependencies

```
pandas>=2.0
openpyxl>=3.1
matplotlib>=3.7
numpy>=1.24
scikit-learn>=1.3
```

All are widely maintained, pip-installable, and have no C-extension compilation requirements on Windows. `tkinter` is part of the Python standard library and requires no separate installation on Windows; on Linux it may require `sudo apt install python3-tk`. `joblib` (used for model persistence) is installed automatically as a dependency of `scikit-learn` — no separate entry in `requirements.txt` is needed.

> **Note:** After setting up the virtual environment and verifying everything works, run `pip freeze > requirements.txt` to replace these minimum-version specifiers with exact pinned versions (e.g. `pandas==2.2.1`) for fully reproducible installs across machines.

---

## 18. Future Improvements

These are listed in priority order. None of them require modifying any existing file — they are all additions under the OCP principle.

| Priority | Improvement | What's Needed |
|---|---|---|
| 1 | Closing Stock Integration | Fill in `closing_stock_loader.py` and `stock_adjusted_forecast.py` stubs |
| 2 | Safety Stock Calculation | New `safety_stock.py` in `analysis/` — uses lead time variance from `LeadTimeCalculator` |
| 3 | EOQ / Re-order Point | New `eoq_strategy.py` — activatable when ordering cost / holding cost data becomes available |
| 4 | Seasonality Detection | New `seasonality_analyzer.py` — flags items where monthly qty variance is high, warns user about flat-average estimates |
| 5 | CSV export option | New `csv_exporter.py` implementing `BaseExporter` |
| 6 | Dark mode for GUI | Add a theme toggle to `app.py` using `ttk.Style` |
| 7 | Automated scheduling | A `scheduler.py` wrapping `main.py` with `schedule` library |
