"""Validated pinhole camera model, JSON persistence, and consistent undistortion."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

from visiongauge.config import ChessboardConfig
from visiongauge.errors import CameraCalibrationError
from visiongauge.image_io import validate_image


def _array(value, shape, name):
    array = np.asarray(value)
    if array.dtype.kind not in "fiu" or array.shape != shape or not np.isfinite(array).all():
        raise CameraCalibrationError(f"{name}: cần mảng số hữu hạn có kích thước {shape}.")
    array = array.astype(np.float64, copy=True)
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class CameraCalibration:
    image_size: tuple[int, int]
    board: ChessboardConfig
    camera_matrix: np.ndarray
    distortion: np.ndarray
    rvecs: np.ndarray
    tvecs: np.ndarray
    view_names: tuple[str, ...]
    per_view_rmse_px: np.ndarray
    rms_px: float

    def __post_init__(self):
        if len(self.image_size) != 2 or any(type(x) is not int or x < 16 for x in self.image_size):
            raise CameraCalibrationError("image_size phải là (width, height) nguyên >= 16.")
        if not isinstance(self.board, ChessboardConfig):
            raise CameraCalibrationError("Cấu hình bàn cờ không hợp lệ.")
        count = len(self.view_names)
        if count < 5 or any(not isinstance(x, str) or not x for x in self.view_names) or len(set(self.view_names)) != count:
            raise CameraCalibrationError("Calibration cần ít nhất 5 tên ảnh hợp lệ, không trùng nhau.")
        for name, shape in (("camera_matrix", (3, 3)), ("distortion", (5,)),
                            ("rvecs", (count, 3)), ("tvecs", (count, 3)), ("per_view_rmse_px", (count,))):
            object.__setattr__(self, name, _array(getattr(self, name), shape, name))
        k = self.camera_matrix
        if (k[0, 0] <= 0 or k[1, 1] <= 0 or not np.allclose(k[2], [0, 0, 1], atol=1e-10)
                or abs(k[0, 1]) > 1e-10 or abs(k[1, 0]) > 1e-10
                or not 0 <= k[0, 2] < self.image_size[0] or not 0 <= k[1, 2] < self.image_size[1]):
            raise CameraCalibrationError("Camera matrix không hợp lệ hoặc tâm ảnh nằm ngoài khung hình.")
        if (type(self.rms_px) not in (float, int) or not np.isfinite(self.rms_px) or self.rms_px < 0
                or np.any(self.per_view_rmse_px < 0) or np.any(self.tvecs[:, 2] <= 0)):
            raise CameraCalibrationError("Sai số reprojection hoặc translation vectors không hợp lệ.")
        if not np.isclose(self.rms_px, np.sqrt(np.mean(self.per_view_rmse_px ** 2)), rtol=1e-5, atol=1e-6):
            raise CameraCalibrationError("RMSE tổng không nhất quán với RMSE từng ảnh.")
        # OpenCV does not constrain radial monotonicity during optimization.
        width, height = self.image_size
        corners = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
        radius = np.linalg.norm((corners - k[:2, 2]) / [k[0, 0], k[1, 1]], axis=1).max()
        r2 = np.linspace(0, radius, 128) ** 2
        k1, k2, _, _, k3 = self.distortion
        if np.any(1 + 3 * k1 * r2 + 5 * k2 * r2 ** 2 + 7 * k3 * r2 ** 3 <= 0):
            raise CameraCalibrationError("Mô hình méo xuyên tâm không đơn điệu trong vùng ảnh; cần chụp lại bộ calibration.")

    @property
    def fingerprint(self) -> str:
        return sha256(calibration_to_json(self)).hexdigest()


def calibration_to_json(calibration: CameraCalibration) -> bytes:
    payload = {
        "schema_version": 1, "model": "opencv_pinhole_5", "units": "mm",
        "image_size": list(calibration.image_size),
        "board": vars(calibration.board), "camera_matrix": calibration.camera_matrix.tolist(),
        "distortion": calibration.distortion.tolist(), "rvecs": calibration.rvecs.tolist(),
        "tvecs": calibration.tvecs.tolist(), "view_names": list(calibration.view_names),
        "per_view_rmse_px": calibration.per_view_rmse_px.tolist(), "rms_px": calibration.rms_px,
    }
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")


def calibration_from_json(data: bytes) -> CameraCalibration:
    try:
        if not isinstance(data, bytes) or len(data) > 5_000_000:
            raise ValueError("JSON calibration phải là bytes và không quá 5 MB.")
        payload = json.loads(data.decode("utf-8-sig"))
        fields = {"schema_version", "model", "units", "image_size", "board", "camera_matrix", "distortion",
                  "rvecs", "tvecs", "view_names", "per_view_rmse_px", "rms_px"}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError("Thiếu khóa hoặc schema calibration không được hỗ trợ.")
        if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["model"] != "opencv_pinhole_5" or payload["units"] != "mm":
            raise ValueError("Chỉ hỗ trợ schema 1, mô hình pinhole 5 hệ số và đơn vị mm.")
        if not isinstance(payload["board"], dict) or set(payload["board"]) != {"columns", "rows", "square_size_mm"}:
            raise ValueError("Calibration thiếu thông số bàn cờ.")
        if not isinstance(payload["view_names"], list) or not isinstance(payload["image_size"], list):
            raise ValueError("view_names và image_size phải là danh sách JSON.")
        return CameraCalibration(
            tuple(payload["image_size"]), ChessboardConfig(**payload["board"]),
            payload["camera_matrix"], payload["distortion"], payload["rvecs"], payload["tvecs"],
            tuple(payload["view_names"]), payload["per_view_rmse_px"], payload["rms_px"],
        )
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise CameraCalibrationError(f"Không nạp được calibration: {exc}") from exc


def save_calibration(path: str | Path, calibration: CameraCalibration) -> None:
    try:
        Path(path).write_bytes(calibration_to_json(calibration))
    except OSError as exc:
        raise CameraCalibrationError(f"Không lưu được calibration: {exc}") from exc


def load_calibration(path: str | Path) -> CameraCalibration:
    try:
        return calibration_from_json(Path(path).read_bytes())
    except OSError as exc:
        raise CameraCalibrationError(f"Không đọc được calibration: {exc}") from exc


def undistort_image(image: np.ndarray, calibration: CameraCalibration) -> np.ndarray:
    image = validate_image(image)
    actual = (image.shape[1], image.shape[0])
    if actual != calibration.image_size:
        raise CameraCalibrationError(
            f"Ảnh {actual[0]} × {actual[1]} khác độ phân giải calibration "
            f"{calibration.image_size[0]} × {calibration.image_size[1]}. Không tự resize/crop hoặc đổi camera matrix."
        )
    try:
        return cv2.undistort(image, calibration.camera_matrix, calibration.distortion, None, calibration.camera_matrix)
    except cv2.error as exc:
        raise CameraCalibrationError("Không khử méo được ảnh bằng calibration này.") from exc


def undistort_image_points(points_px: np.ndarray, calibration: CameraCalibration) -> np.ndarray:
    """Return pixel coordinates in the SAME K/output frame as undistort_image."""
    points = np.asarray(points_px, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or not len(points) or not np.isfinite(points).all():
        raise CameraCalibrationError("Tọa độ góc cần có dạng N × 2 hữu hạn.")
    return cv2.undistortPointsIter(
        points.reshape(-1, 1, 2), calibration.camera_matrix, calibration.distortion,
        None, calibration.camera_matrix, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-10),
    ).reshape(-1, 2)
