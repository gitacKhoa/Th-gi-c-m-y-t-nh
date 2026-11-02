"""Rectangle validation and dimensions computed ONLY in the metric plane."""

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

from visiongauge.errors import UnreliableMeasurementError


@dataclass(frozen=True)
class RectangleOptions:
    min_rectangularity: float = 0.94
    approximation_fraction: float = 0.015
    max_angle_deviation_deg: float = 8.0
    max_opposite_side_difference: float = 0.10

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} phải là số hữu hạn > 0.")
        if not 0 < self.min_rectangularity <= 1:
            raise ValueError("min_rectangularity phải nằm trong (0, 1].")
        if self.approximation_fraction >= 0.1:
            raise ValueError("approximation_fraction phải nhỏ hơn 0.1.")
        if self.max_angle_deviation_deg >= 45 or self.max_opposite_side_difference >= 1:
            raise ValueError("Ngưỡng kiểm tra hình chữ nhật quá lớn.")


@dataclass(frozen=True)
class RectangleGeometry:
    length_mm: float
    width_mm: float
    corners_mm: np.ndarray
    rectangularity: float


def fit_metric_rectangle(
    contour_mm: np.ndarray, options: RectangleOptions | None = None,
) -> RectangleGeometry:
    """Validate a convex quadrilateral, then fit its metric enclosing rectangle.

    Length is always the longer side. The fit uses the full transformed contour,
    not a rotated bounding box or a single pixel/mm ratio in the source image.
    """
    options = options or RectangleOptions()
    points = np.asarray(contour_mm, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 4 or not np.isfinite(points).all():
        raise UnreliableMeasurementError("Đường bao mm phải có ít nhất 4 điểm hữu hạn.")
    contour = points.astype(np.float32).reshape(-1, 1, 2)
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        raise UnreliableMeasurementError("Đường bao sản phẩm suy biến.")
    quad = cv2.approxPolyDP(contour, options.approximation_fraction * perimeter, True)
    if len(quad) != 4 or not cv2.isContourConvex(quad):
        raise UnreliableMeasurementError("Sản phẩm không có đường bao tứ giác lồi.")
    edges = np.roll(quad.reshape(4, 2), -1, axis=0) - quad.reshape(4, 2)
    sides = np.linalg.norm(edges, axis=1)
    if np.min(sides) <= 1e-6:
        raise UnreliableMeasurementError("Cạnh sản phẩm suy biến.")
    cosines = np.sum(edges * np.roll(edges, -1, axis=0), axis=1) / (sides * np.roll(sides, -1))
    if np.any(np.abs(cosines) > np.sin(np.deg2rad(options.max_angle_deviation_deg))):
        raise UnreliableMeasurementError("Các cạnh không vuông góc trong mặt phẳng mm.")
    differences = np.abs(sides[:2] - sides[2:]) / np.maximum(sides[:2], sides[2:])
    if np.any(differences > options.max_opposite_side_difference):
        raise UnreliableMeasurementError("Các cạnh đối diện không bằng nhau trong mặt phẳng mm.")
    rectangle = cv2.minAreaRect(contour)
    side_a, side_b = rectangle[1]
    if min(side_a, side_b) <= 1e-6:
        raise UnreliableMeasurementError("Kích thước sản phẩm suy biến.")
    rectangularity = float(cv2.contourArea(contour) / (side_a * side_b))
    if rectangularity < options.min_rectangularity:
        raise UnreliableMeasurementError("Đường bao thiếu cạnh, bị che hoặc không đủ giống hình chữ nhật.")
    return RectangleGeometry(
        float(max(side_a, side_b)), float(min(side_a, side_b)),
        cv2.boxPoints(rectangle).astype(np.float64), rectangularity,
    )
