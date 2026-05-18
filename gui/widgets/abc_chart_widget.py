# gui/widgets/abc_chart_widget.py
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ABCChartWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def plot(self, df: pd.DataFrame) -> None:
        self.figure.clear()
        if df.empty or 'total_value' not in df.columns or 'abc_class' not in df.columns:
            return

        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        df_sorted = df.sort_values('total_value', ascending=False).reset_index(drop=True)
        n = len(df_sorted)

        x_pct = [(i + 1) / n * 100 for i in range(n)]
        y_val = df_sorted['total_value'].values
        y_pct = df_sorted['cumulative_value_pct'].values

        # Enforce logarithmic scaling on the primary axis to handle hyper-skewed distributions
        ax1.set_yscale('log', nonpositive='clip')

        # Establish safe lower bounds for the log scale tracking
        min_positive_val = y_val[y_val > 0].min() if (y_val > 0).any() else 1.0
        max_val = y_val.max() if y_val.max() > 0 else 10.0

        # Apply a small padding buffer to the log boundaries
        ax1.set_ylim(bottom=max(0.1, min_positive_val * 0.5), top=max_val * 2.0)

        # --- Derive A/B and B/C boundaries from classifier output ---
        a_indices = df_sorted.index[df_sorted['abc_class'] == 'A']
        b_indices = df_sorted.index[df_sorted['abc_class'] == 'B']

        x_ab = x_pct[a_indices[-1]] if len(a_indices) else 0.0
        x_bc = x_pct[b_indices[-1]] if len(b_indices) else x_ab
        y_ab = y_pct[a_indices[-1]] if len(a_indices) else 70.0
        y_bc = y_pct[b_indices[-1]] if len(b_indices) else 90.0

        # --- ABC background zones ---
        ax1.axvspan(0, x_ab, alpha=0.15, color='#EAE2B7', zorder=0)
        ax1.axvspan(x_ab, x_bc, alpha=0.15, color='#FCBF49', zorder=0)
        ax1.axvspan(x_bc, 100, alpha=0.15, color='#F77F00', zorder=0)

        # --- Vertical boundary lines ---
        ax1.axvline(x_ab, color='gray', linestyle='--', linewidth=0.9, zorder=1)
        ax1.axvline(x_bc, color='gray', linestyle='--', linewidth=0.9, zorder=1)

        # --- Horizontal threshold lines (on ax2 scale) ---
        ax2.axhline(y_ab, color='steelblue', linestyle='--', linewidth=0.9)
        ax2.axhline(y_bc, color='steelblue', linestyle='--', linewidth=0.9)

        # High-density visualization override: Use fill_between to eliminate bar overlap artifacts
        ax1.fill_between(x_pct, max(0.1, min_positive_val * 0.5), y_val,
                         step="pre", color='#003049', alpha=0.85, zorder=2)

        # Cumulative trajectory line
        ax2.plot(x_pct, y_pct, color='#ff0844', linewidth=2, zorder=3)

        # --- Zone labels via axes-fraction transform ---
        label_y_frac = 0.85
        ax1.text(x_ab / 200, label_y_frac, 'A', transform=ax1.transAxes,
                 ha='center', fontsize=13, color='#000000', fontweight='bold')
        ax1.text((x_ab + x_bc) / 200, label_y_frac, 'B', transform=ax1.transAxes,
                 ha='center', fontsize=13, color='#000000', fontweight='bold')
        ax1.text((x_bc + 100) / 200, label_y_frac, 'C', transform=ax1.transAxes,
                 ha='center', fontsize=13, color='#000000', fontweight='bold')

        # --- X-axis: standard ticks + exact boundary values ---
        std_x = list(range(0, 101, 20))
        boundary_x = [round(x_ab, 2), round(x_bc, 2)]
        all_x = sorted(set(std_x + boundary_x))
        ax1.set_xticks(all_x)
        x_labels = ax1.set_xticklabels(
            [f'{t:.2f}%' if t in boundary_x else f'{int(t)}%' for t in all_x],
            rotation=45, ha='right', fontsize=8
        )
        for label, t in zip(x_labels, all_x):
            if t in boundary_x:
                label.set_fontweight('bold')

        # --- Right Y-axis: standard ticks + exact threshold values ---
        std_y = list(range(0, 101, 20))
        boundary_y = [round(y_ab, 2), round(y_bc, 2)]
        all_y = sorted(set(std_y + boundary_y))
        ax2.set_yticks(all_y)
        y_labels = ax2.set_yticklabels(
            [f'{t:.2f}%' if t in boundary_y else f'{int(t)}%' for t in all_y],
            fontsize=8
        )
        for label, t in zip(y_labels, all_y):
            if t in boundary_y:
                label.set_fontweight('bold')

        ax1.set_xlim(0, 100)
        ax2.set_ylim(0, 100)
        ax1.set_xlabel('Cumulative % of items in inventory', fontweight='bold')
        ax1.set_ylabel('Total Value (Log Scale)', color='#4facfe', fontweight='bold')
        ax2.set_ylabel('Cumulative % of total inventory value', color='#ff0844', fontweight='bold')
        ax1.set_title('ABC Pareto Analysis (Logarithmic Resolution)', fontweight='bold')

        ax1.grid(True, which="both", linestyle=":", alpha=0.3, zorder=0)

        self.figure.tight_layout()
        self.canvas.draw()