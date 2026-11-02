"""Multi-view camera calibration using complete Chessboard observations."""

from dataclasses import dataclass
from hashlib import sha256

import cv2
import numpy as np

from visiongauge.config import ChessboardConfig
from visiongauge.errors import CameraCalibrationError, VisionGaugeError
from visiongauge.image_io import decode_image
from .chessboard import chessboard_points_mm, detect_chessboard
from .camera_model import CameraCalibration


MIN_CALIBRATION_VIEWS = 5


@dataclass(frozen=True)
class CalibrationView:
    name: str
    image_size: tuple[int, int]
    corners_px: np.ndarray


@dataclass(frozen=True)
class CalibrationScan:
    views: tuple[CalibrationView, ...]
    failures: tuple[tuple[str, str], ...]


def scan_calibration_images(images: list[tuple[str, bytes]], board: ChessboardConfig) -> CalibrationScan:
    views, failures, hashes = [], [], set()
    if len({name for name, _ in images}) != len(images):
        raise CameraCalibrationError("Tên ảnh hiệu chuẩn bị trùng; hãy đổi tên để phân biệt từng ảnh.")
    size = None
    for name, data in images:
        try:
            digest = sha256(data).hexdigest()
            if digest in hashes:
                raise CameraCalibrationError("Ảnh trùng nội dung; không được tính như một góc chụp mới.")
            hashes.add(digest)
            image = decode_image(data)
            current_size = (image.shape[1], image.shape[0])
            if size is not None and size != current_size:
                raise CameraCalibrationError(f"Khác độ phân giải chuẩn {size}; không resize ảnh hiệu chuẩn.")
            detection = detect_chessboard(image, board)
            size = current_size
            views.append(CalibrationView(name, size, detection.corners_px.copy()))
        except VisionGaugeError as exc:
            failures.append((name, str(exc)))
    return CalibrationScan(tuple(views), tuple(failures))


def _check_pose_diversity(views: tuple[CalibrationView, ...], board: ChessboardConfig) -> None:
    """Check rank of Zhang's intrinsic constraints using normalized image coordinates."""
    constraints = []
    world = chessboard_points_mm(board)

    def v(h, i, j):
        return np.array([h[0, i] * h[0, j], h[0, i] * h[1, j] + h[1, i] * h[0, j],
                         h[1, i] * h[1, j], h[2, i] * h[0, j] + h[0, i] * h[2, j],
                         h[2, i] * h[1, j] + h[1, i] * h[2, j], h[2, i] * h[2, j]])

    for view in views:
        normalized = view.corners_px / np.array(view.image_size)
        h, _ = cv2.findHomography(world, normalized, method=0)
        if h is None:
            raise CameraCalibrationError("Góc bàn cờ suy biến.")
        for row in (v(h, 0, 1), v(h, 0, 0) - v(h, 1, 1)):
            norm = np.linalg.norm(row)
            if norm <= 1e-15:
                raise CameraCalibrationError("Góc chụp bàn cờ suy biến.")
            constraints.append(row / norm)
    singular = np.linalg.svd(np.asarray(constraints), compute_uv=False)
    if singular[-2] / singular[0] < 1e-4:
        raise CameraCalibrationError("Các góc chụp chưa đủ đa dạng; cần nghiêng bàn cờ theo nhiều hướng, không chỉ dịch chuyển/xoay trong mặt phẳng.")


def calibrate_camera(
    views: tuple[CalibrationView, ...], board: ChessboardConfig, *,
    max_rms_px: float = 1.0, max_view_rmse_px: float = 2.0,
) -> CameraCalibration:
    if not isinstance(board, ChessboardConfig):
        raise CameraCalibrationError("Cấu hình bàn cờ không hợp lệ.")
    if any(type(x) not in (int, float) or not np.isfinite(x) or x <= 0 for x in (max_rms_px, max_view_rmse_px)):
        raise CameraCalibrationError("Ngưỡng reprojection error phải là số hữu hạn > 0.")
    if len(views) < MIN_CALIBRATION_VIEWS:
        raise CameraCalibrationError(f"Cần ít nhất {MIN_CALIBRATION_VIEWS} ảnh tìm đủ góc; hiện có {len(views)}. Khuyến nghị 15–25 ảnh đa dạng.")
    size = views[0].image_size
    if len(size) != 2 or any(type(x) is not int or x < 16 for x in size):
        raise CameraCalibrationError("Độ phân giải ảnh hiệu chuẩn không hợp lệ.")
    count = board.columns * board.rows
    names = tuple(view.name for view in views)
    if len(set(names)) != len(names):
        raise CameraCalibrationError("Tên ảnh hiệu chuẩn bị trùng.")
    for view in views:
        points = np.asarray(view.corners_px)
        if (view.image_size != size or points.shape != (count, 2) or not np.isfinite(points).all()
                or np.any(points < 0) or np.any(points >= np.array(size))):
            raise CameraCalibrationError(f"Ảnh {view.name}: số góc, tọa độ hoặc độ phân giải không hợp lệ.")
    _check_pose_diversity(views, board)
    world = np.column_stack((chessboard_points_mm(board), np.zeros(count))).astype(np.float32)
    image_points = [np.asarray(view.corners_px, dtype=np.float32).reshape(-1, 1, 2) for view in views]
    try:
        _, matrix, distortion, rotations, translations = cv2.calibrateCamera(
            [world.copy() for _ in views], image_points, size, None, None,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-9),
        )
        errors = []
        for observed, rotation, translation in zip(image_points, rotations, translations):
            projected, _ = cv2.projectPoints(world, rotation, translation, matrix, distortion)
            residual = projected.reshape(-1, 2).astype(float) - observed.reshape(-1, 2)
            errors.append(float(np.sqrt(np.mean(np.sum(residual ** 2, axis=1)))))
    except cv2.error as exc:
        raise CameraCalibrationError("OpenCV không giải được bài toán calibration; kiểm tra bộ ảnh và cấu hình.") from exc
    rms = float(np.sqrt(np.mean(np.square(errors))))
    if not np.isfinite(rms) or rms > max_rms_px or max(errors) > max_view_rmse_px:
        raise CameraCalibrationError(f"Calibration không đạt ngưỡng: RMS={rms:.3f} px, max ảnh={max(errors):.3f} px ({names[int(np.argmax(errors))]}). Không tự loại ảnh để che giấu lỗi.")
    return CameraCalibration(
        size, board, matrix, distortion.reshape(-1), np.asarray(rotations).reshape(-1, 3),
        np.asarray(translations).reshape(-1, 3), names, np.asarray(errors), rms,
    )
