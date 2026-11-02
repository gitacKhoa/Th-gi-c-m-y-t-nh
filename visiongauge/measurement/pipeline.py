"""Headless rectangular-product measurement with explicit failure states."""

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from visiongauge.calibration import (
    ChessboardDetection, MappingOptions, PlanarMapping, detect_chessboard, estimate_planar_mapping,
)
from visiongauge.config import ChessboardConfig
from visiongauge.errors import (
    AmbiguousProductError, CalibrationRequiredError, ProductNotFoundError,
    UnreliableMappingError, UnreliableMeasurementError,
)
from visiongauge.image_io import validate_image
from visiongauge.processing import ContourOptions, extract_product_contours
from .annotation import annotate_measurement
from .geometry import RectangleGeometry, RectangleOptions, fit_metric_rectangle


@dataclass(frozen=True)
class MeasurementResult:
    rectangle: RectangleGeometry
    corners_px: np.ndarray
    board: ChessboardDetection
    mapping: PlanarMapping
    annotated_image: np.ndarray
    segmentation_mask: np.ndarray
    warnings: tuple[str, ...]

    @property
    def length_mm(self) -> float:
        return self.rectangle.length_mm

    @property
    def width_mm(self) -> float:
        return self.rectangle.width_mm


def _same_boundary(first: RectangleGeometry, second: RectangleGeometry) -> bool:
    """Merge only near-identical outlines, e.g. both edges of a Canny contour."""
    a = first.corners_mm.astype(np.float32)
    b = second.corners_mm.astype(np.float32)
    intersection, _ = cv2.intersectConvexConvex(a, b)
    union = cv2.contourArea(a) + cv2.contourArea(b) - intersection
    return union > 0 and intersection / union > 0.85


def measure_rectangle(
    image: np.ndarray,
    board_config: ChessboardConfig,
    *,
    image_geometry: Literal["undistorted", "negligible_distortion"] | None = None,
    detector: Literal["auto", "sb", "classic"] = "auto",
    mapping_options: MappingOptions | None = None,
    contour_options: ContourOptions | None = None,
    rectangle_options: RectangleOptions | None = None,
) -> MeasurementResult:
    """Measure exactly one rectangle coplanar with the fully visible chessboard.

    The caller must supply an already undistorted image, or explicitly state
    that lens distortion is negligible. This declaration is not verified by a
    homography fit and is never inferred from a low reprojection error.
    Errors inherit VisionGaugeError; callers must not treat them as tolerance FAIL.
    """
    validate_image(image)
    if image_geometry not in ("undistorted", "negligible_distortion"):
        raise CalibrationRequiredError(
            "Chưa xác nhận điều kiện méo ảnh. Cần ảnh đã khử méo (undistorted) "
            "hoặc xác nhận méo không đáng kể (negligible_distortion). "
            "Homography không thay thế hiệu chỉnh méo ống kính."
        )
    detection = detect_chessboard(image, board_config, method=detector)
    mapping = estimate_planar_mapping(detection.corners_px, board_config, mapping_options)
    segmented = extract_product_contours(image, mapping, contour_options)
    candidates = []
    mapping_failures = []
    for contour in segmented.contours_px:
        try:
            metric_contour = mapping.to_mm(contour)
        except UnreliableMappingError as exc:
            mapping_failures.append(str(exc))
            continue
        try:
            rectangle = fit_metric_rectangle(metric_contour, rectangle_options)
        except UnreliableMeasurementError:
            continue
        # The fitted box must also stay inside the image and the valid mapping.
        box_px = mapping.to_image(rectangle.corners_mm)
        if np.any(box_px < 0) or np.any(box_px >= np.array([image.shape[1], image.shape[0]])):
            continue
        mapping.to_mm(box_px)
        if not any(_same_boundary(rectangle, previous) for previous in candidates):
            candidates.append(rectangle)
    if mapping_failures:
        # Do not silently choose another object when an eligible large contour
        # cannot be mapped. That could return the wrong product's dimensions.
        raise UnreliableMeasurementError("Không thể ánh xạ sản phẩm: " + mapping_failures[0])
    if not candidates:
        raise ProductNotFoundError(
            "Không tìm thấy sản phẩm chữ nhật hoàn chỉnh tách biệt với bàn cờ. "
            "Kiểm tra độ tương phản, vật bị che/cắt mép và ngưỡng tách ảnh."
        )
    if len(candidates) != 1:
        raise AmbiguousProductError(
            f"Có {len(candidates)} sản phẩm ứng viên; cần đúng một sản phẩm trong ảnh."
        )
    rectangle = candidates[0]
    corners_px = mapping.to_image(rectangle.corners_mm)
    warnings = [
        "Sai số chiếu lại bàn cờ không phải độ không đảm bảo đo hoặc độ chính xác thực nghiệm.",
        "Giả thiết sản phẩm và bàn cờ đồng phẳng phải được bảo đảm khi chụp.",
    ]
    if image_geometry == "negligible_distortion":
        warnings.append("Đang dùng giả thiết méo ống kính không đáng kể do người gọi xác nhận.")
    return MeasurementResult(
        rectangle, corners_px, detection, mapping,
        annotate_measurement(image, detection, corners_px, rectangle.length_mm, rectangle.width_mm, rectangle.corners_mm),
        segmented.mask, tuple(warnings),
    )
