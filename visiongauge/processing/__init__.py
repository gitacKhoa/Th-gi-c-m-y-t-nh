"""Preprocessing and product-contour extraction, independent of the UI."""

from .contours import ContourOptions, SegmentationResult, extract_product_contours

__all__ = ["ContourOptions", "SegmentationResult", "extract_product_contours"]
