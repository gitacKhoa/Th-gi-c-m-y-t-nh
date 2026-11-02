"""Validated image-to-mm homography; this module does NOT correct lens distortion."""

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

from visiongauge.config import ChessboardConfig
from visiongauge.errors import UnreliableMappingError
from .chessboard import chessboard_points_mm


@dataclass(frozen=True)
class MappingOptions:
    min_corner_spacing_px: float = 8.0
    max_rmse_px: float = 0.6
    max_error_px: float = 1.5
    max_cell_aspect: float = 5.0
    max_extrapolation_squares: float = 10.0

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) not in (float, int) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} phải là số hữu hạn > 0.")
        if self.max_cell_aspect < 1 or self.max_error_px < self.max_rmse_px:
            raise ValueError("Ngưỡng aspect hoặc sai số homography không hợp lệ.")


@dataclass(frozen=True)
class MappingQuality:
    rmse_px: float
    max_error_px: float
    rmse_mm: float
    min_corner_spacing_px: float


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Project Nx2 points explicitly, rejecting nonfinite coordinates and poles."""
    points = np.asarray(points, dtype=np.float64)
    matrix = np.asarray(matrix, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) == 0:
        raise UnreliableMappingError("Tọa độ phải có dạng N × 2, N > 0.")
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or not np.isfinite(points).all():
        raise UnreliableMappingError("Tọa độ/ma trận chứa giá trị không hợp lệ.")
    scale = np.max(np.abs(matrix))
    if scale == 0 or np.linalg.matrix_rank(matrix / scale) < 3:
        raise UnreliableMappingError("Ma trận homography suy biến.")
    matrix = matrix / scale
    homogeneous = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    denominator = homogeneous[:, 2]
    # A polygon crossing the projective horizon cannot represent a finite object.
    if np.any(np.abs(denominator) < 1e-10) or np.min(denominator) * np.max(denominator) <= 0:
        raise UnreliableMappingError("Ánh xạ ở gần hoặc đi qua đường chân trời phối cảnh.")
    result = homogeneous[:, :2] / denominator[:, None]
    if not np.isfinite(result).all():
        raise UnreliableMappingError("Kết quả ánh xạ không hữu hạn.")
    return result


@dataclass(frozen=True)
class PlanarMapping:
    image_to_mm: np.ndarray
    mm_to_image: np.ndarray
    config: ChessboardConfig
    corners_px: np.ndarray
    quality: MappingQuality
    options: MappingOptions

    def to_mm(self, points: np.ndarray) -> np.ndarray:
        # Include board points so objects on the other side of a pole are rejected.
        points = np.asarray(points, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2 or not len(points):
            raise UnreliableMappingError("Tọa độ phải có dạng N × 2, N > 0.")
        result = transform_points(np.vstack((self.corners_px, points)), self.image_to_mm)
        result = result[len(self.corners_px):]
        margin = self.options.max_extrapolation_squares * self.config.square_size_mm
        upper = np.array([self.config.columns - 1, self.config.rows - 1]) * self.config.square_size_mm
        epsilon_mm = self.config.square_size_mm * 1e-6
        if np.any(result < -margin - epsilon_mm) or np.any(result > upper + margin + epsilon_mm):
            raise UnreliableMappingError("Sản phẩm quá xa vùng bàn cờ để ngoại suy tin cậy.")
        return result

    def to_image(self, points_mm: np.ndarray) -> np.ndarray:
        return transform_points(points_mm, self.mm_to_image)

    def board_polygon_px(self, margin_squares: float = 0.25) -> np.ndarray:
        """Whole board (outer squares included), with a small exclusion margin."""
        s = self.config.square_size_mm
        low = -(1 + margin_squares) * s
        right = (self.config.columns + margin_squares) * s
        bottom = (self.config.rows + margin_squares) * s
        return self.to_image(np.array([[low, low], [right, low], [right, bottom], [low, bottom]]))


def estimate_planar_mapping(
    corners_px: np.ndarray, config: ChessboardConfig, options: MappingOptions | None = None,
) -> PlanarMapping:
    """Fit all grid corners; reject bad fits instead of hiding corners as outliers."""
    options = options or MappingOptions()
    corners = np.asarray(corners_px, dtype=np.float64)
    if corners.shape == (config.rows * config.columns, 1, 2):
        corners = corners.reshape(-1, 2)
    if corners.shape != (config.rows * config.columns, 2) or not np.isfinite(corners).all():
        raise UnreliableMappingError("Thiếu góc bàn cờ hoặc tọa độ góc không hợp lệ.")
    grid = corners.reshape(config.rows, config.columns, 2)
    horizontal = np.linalg.norm(np.diff(grid, axis=1), axis=2)
    vertical = np.linalg.norm(np.diff(grid, axis=0), axis=2)
    spacing = float(min(horizontal.min(), vertical.min()))
    if spacing < options.min_corner_spacing_px:
        raise UnreliableMappingError("Bàn cờ quá nhỏ hoặc các góc trùng nhau.")
    if max(horizontal.max(), vertical.max()) / spacing > options.max_cell_aspect:
        raise UnreliableMappingError("Phối cảnh bàn cờ quá xiên hoặc lưới góc bị lỗi.")
    signs = []
    for row in range(config.rows - 1):
        for col in range(config.columns - 1):
            quad = grid[[row, row, row + 1, row + 1], [col, col + 1, col + 1, col]].astype(np.float32)
            if not cv2.isContourConvex(quad):
                raise UnreliableMappingError("Lưới góc bàn cờ bị gấp hoặc suy biến.")
            signs.append(np.sign(cv2.contourArea(quad, oriented=True)))
    if len(set(signs)) != 1:
        raise UnreliableMappingError("Thứ tự góc bàn cờ không nhất quán.")
    real = chessboard_points_mm(config)
    try:
        matrix, _ = cv2.findHomography(corners, real, method=0)
        if matrix is None:
            raise UnreliableMappingError("Không tính được homography.")
        inverse = np.linalg.inv(matrix)
    except (cv2.error, np.linalg.LinAlgError) as exc:
        raise UnreliableMappingError("Homography suy biến.") from exc
    projected_px = transform_points(real, inverse)
    projected_mm = transform_points(corners, matrix)
    errors = np.linalg.norm(projected_px - corners, axis=1)
    quality = MappingQuality(
        float(np.sqrt(np.mean(errors ** 2))), float(errors.max()),
        float(np.sqrt(np.mean(np.sum((projected_mm - real) ** 2, axis=1)))), spacing,
    )
    if quality.rmse_px > options.max_rmse_px or quality.max_error_px > options.max_error_px:
        raise UnreliableMappingError(
            f"Homography không đáng tin cậy: RMSE={quality.rmse_px:.3f} px, "
            f"max={quality.max_error_px:.3f} px. Kiểm tra góc và méo ống kính."
        )
    return PlanarMapping(matrix, inverse, config, corners.copy(), quality, options)
