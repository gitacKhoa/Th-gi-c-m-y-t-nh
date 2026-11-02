"""Full-grid chessboard detection and subpixel corner localization."""

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from visiongauge.config import ChessboardConfig
from visiongauge.errors import ChessboardNotFoundError
from visiongauge.image_io import to_bgr, to_gray


@dataclass(frozen=True)
class ChessboardDetection:
    corners_px: np.ndarray
    points_mm: np.ndarray
    config: ChessboardConfig
    method: str


def chessboard_points_mm(config: ChessboardConfig) -> np.ndarray:
    """Row-major Nx2 grid: first inner corner is (0, 0), axes follow detection.

    An unmarked symmetric board can reverse its origin/axes between captures.
    This does not change lengths; persistent object poses are not provided.
    """
    x, y = np.meshgrid(np.arange(config.columns), np.arange(config.rows))
    return np.column_stack((x.ravel(), y.ravel())).astype(np.float64) * config.square_size_mm


def detect_chessboard(
    image: np.ndarray,
    config: ChessboardConfig,
    *,
    method: Literal["auto", "sb", "classic"] = "auto",
) -> ChessboardDetection:
    """Use SB's native subpixel estimates, or cornerSubPix for classic detection."""
    if method not in ("auto", "sb", "classic"):
        raise ValueError("method phải là auto, sb hoặc classic.")
    gray = to_gray(image)
    found, corners = False, None
    used = "sb"
    try:
        if method in ("auto", "sb"):
            found, corners = cv2.findChessboardCornersSB(
                gray, config.pattern_size,
                flags=cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_ACCURACY,
            )
        if not found and method in ("auto", "classic"):
            used = "classic"
            found, corners = cv2.findChessboardCorners(
                gray, config.pattern_size,
                flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE,
            )
            if found:
                # Window stays smaller than half the nearest grid spacing.
                grid = corners.reshape(config.rows, config.columns, 2)
                spacing = min(
                    np.linalg.norm(np.diff(grid, axis=0), axis=2).min(),
                    np.linalg.norm(np.diff(grid, axis=1), axis=2).min(),
                )
                radius = max(1, min(5, int(spacing / 4)))
                corners = cv2.cornerSubPix(
                    gray, corners, (radius, radius), (-1, -1),
                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 50, 0.001),
                )
    except cv2.error as exc:
        raise ChessboardNotFoundError("OpenCV không tìm được bàn cờ hoàn chỉnh.") from exc
    if not found or corners is None or len(corners) != config.columns * config.rows:
        raise ChessboardNotFoundError(
            f"Không tìm đủ {config.columns} × {config.rows} góc trong; "
            "kiểm tra cấu hình, độ nét và phần bàn cờ bị che khuất."
        )
    return ChessboardDetection(
        corners.reshape(-1, 2).astype(np.float64), chessboard_points_mm(config), config, used,
    )


def draw_chessboard(image: np.ndarray, detection: ChessboardDetection) -> np.ndarray:
    annotated = to_bgr(image)
    cv2.drawChessboardCorners(
        annotated, detection.config.pattern_size,
        detection.corners_px.astype(np.float32).reshape(-1, 1, 2), True,
    )
    return annotated
