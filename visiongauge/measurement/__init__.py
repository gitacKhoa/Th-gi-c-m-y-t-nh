"""Metric rectangle geometry and a UI-independent measurement pipeline."""

from .geometry import RectangleGeometry, RectangleOptions, fit_metric_rectangle
from .pipeline import MeasurementResult, measure_rectangle

__all__ = [
    "RectangleGeometry", "RectangleOptions", "fit_metric_rectangle",
    "MeasurementResult", "measure_rectangle",
]
