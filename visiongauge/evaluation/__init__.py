"""Experimental evaluation, independent of Streamlit and tolerance classification."""

from .batch import EvaluationReport, evaluate_dataset
from .dataset import read_manifest
from .metrics import error_statistics, measurement_errors
from .summary import summarize_results

__all__ = ["EvaluationReport", "evaluate_dataset", "read_manifest", "error_statistics",
           "measurement_errors", "summarize_results"]
