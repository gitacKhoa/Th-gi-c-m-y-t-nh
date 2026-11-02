"""Classical segmentation and exclusion of the entire chessboard region."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

import cv2
import numpy as np

from visiongauge.calibration import PlanarMapping
from visiongauge.image_io import to_gray


@dataclass(frozen=True)
class ContourOptions:
    method: Literal["threshold", "canny"] = "threshold"
    blur_kernel: int = 5
    min_area_px: float = 250.0
    min_short_side_px: float = 10.0
    border_margin_px: int = 2
    board_margin_squares: float = 0.25
    canny_low: float = 50.0
    canny_high: float = 150.0

    def __post_init__(self) -> None:
        if self.method not in ("threshold", "canny"):
            raise ValueError("method phải là threshold hoặc canny.")
        if type(self.blur_kernel) is not int or self.blur_kernel < 1 or self.blur_kernel % 2 == 0:
            raise ValueError("blur_kernel phải là số nguyên lẻ dương.")
        if type(self.border_margin_px) is not int or self.border_margin_px < 0:
            raise ValueError("border_margin_px phải là số nguyên không âm.")
        for name in ("min_area_px", "min_short_side_px", "canny_high"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} phải là số hữu hạn > 0.")
        for name in ("board_margin_squares", "canny_low"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"{name} phải là số hữu hạn >= 0.")
        if self.canny_low >= self.canny_high:
            raise ValueError("canny_low phải nhỏ hơn canny_high.")


@dataclass(frozen=True)
class SegmentationResult:
    contours_px: tuple[np.ndarray, ...]
    mask: np.ndarray


def extract_product_contours(
    image: np.ndarray, mapping: PlanarMapping, options: ContourOptions | None = None,
) -> SegmentationResult:
    """Return complete contours outside the board, without creating masking edges.

    RETR_LIST permits either dark products or bright product holes in a dark
    background. Canny may yield duplicate inner/outer contours; the measurement
    layer merges those only after confirming their metric rectangle geometry.
    """
    options = options or ContourOptions()
    gray = to_gray(image)
    blurred = cv2.GaussianBlur(gray, (options.blur_kernel, options.blur_kernel), 0)
    if options.method == "threshold":
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    else:
        mask = cv2.Canny(blurred, options.canny_low, options.canny_high)
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    board = cv2.convexHull(mapping.board_polygon_px(options.board_margin_squares).astype(np.float32))
    height, width = gray.shape
    margin = options.border_margin_px
    kept = []
    for contour in contours:
        if cv2.contourArea(contour) < options.min_area_px:
            continue
        points = contour.reshape(-1, 2)
        if (
            np.any(points[:, 0] <= margin) or np.any(points[:, 0] >= width - 1 - margin)
            or np.any(points[:, 1] <= margin) or np.any(points[:, 1] >= height - 1 - margin)
        ):
            continue
        if min(cv2.minAreaRect(contour)[1]) < options.min_short_side_px:
            continue
        hull = cv2.convexHull(points.astype(np.float32))
        intersection_area, _ = cv2.intersectConvexConvex(hull, board)
        if intersection_area > 0:
            continue
        kept.append(points.astype(np.float64))
    return SegmentationResult(tuple(kept), mask)
