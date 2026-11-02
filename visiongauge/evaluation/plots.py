"""Headless Matplotlib figures: references against measurements in millimetres."""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd


def comparison_figure(results: pd.DataFrame) -> Figure:
    successful = results[results.status == "success"]
    figure = Figure(figsize=(10, 4.5), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 2)
    for axis, dimension in zip(axes, ("length", "width")):
        axis.set_title(dimension.capitalize())
        axis.set_xlabel("Caliper reference (mm)")
        axis.set_ylabel("VisionGauge measurement (mm)")
        axis.grid(alpha=0.25)
        if successful.empty:
            axis.text(0.5, 0.5, "No successful measurements", ha="center", va="center", transform=axis.transAxes)
            continue
        reference = successful[f"reference_{dimension}_mm"].to_numpy(dtype=float)
        measured = successful[f"measured_{dimension}_mm"].to_numpy(dtype=float)
        if not np.isfinite([reference, measured]).all():
            raise ValueError("Kết quả thành công không được chứa NaN/vô cực.")
        axis.scatter(reference, measured, alpha=0.75, color="#334155", label="Measured samples")
        low, high = float(min(reference.min(), measured.min())), float(max(reference.max(), measured.max()))
        margin = max((high - low) * 0.1, 0.5)
        bounds = (low - margin, high + margin)
        axis.plot(bounds, bounds, linestyle="--", color="#94a3b8", label="Measured = reference")
        axis.set_xlim(bounds)
        axis.set_ylim(bounds)
        axis.set_aspect("equal", adjustable="box")
        axis.legend(fontsize=8)
    figure.suptitle(f"Successful images: {len(successful)}/{len(results)}; excluded: {len(results) - len(successful)}")
    return figure
