# gui/widgets/abc_chart_widget.py
import pandas as pd
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
        if df.empty or 'total_value' not in df.columns:
            return

        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        df_sorted = df.sort_values('total_value', ascending=False).head(100)
        x = range(len(df_sorted))

        ax1.bar(x, df_sorted['total_value'], color='#4facfe', alpha=0.7)
        ax2.plot(x, df_sorted['cumulative_value_pct'], color='#ff0844', marker='.', linewidth=2)

        ax1.set_ylabel('Total Value', color='#333333', fontweight='bold')
        ax2.set_ylabel('Cumulative %', color='#ff0844', fontweight='bold')
        ax1.set_title('Pareto Analysis (Top 100 Items)', fontweight='bold')

        self.figure.tight_layout()
        self.canvas.draw()