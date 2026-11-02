"""Strict image input, with Unicode Windows paths supported by byte decoding."""

from pathlib import Path

import cv2
import numpy as np

from visiongauge.errors import InvalidImageError


def validate_image(image: np.ndarray) -> np.ndarray:
    """Accept nonempty uint8 grayscale/BGR/BGRA; never rescale values silently."""
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise InvalidImageError("Ảnh phải là numpy.ndarray có kiểu uint8.")
    if image.ndim not in (2, 3) or min(image.shape[:2]) < 16:
        raise InvalidImageError("Ảnh không hợp lệ: cần ít nhất 16 × 16 pixel.")
    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise InvalidImageError("Ảnh chỉ hỗ trợ grayscale, BGR hoặc BGRA.")
    if image.ndim == 3 and image.shape[2] == 4 and np.any(image[:, :, 3] != 255):
        raise InvalidImageError("Ảnh trong suốt phải được ghép với nền trước khi đo.")
    return np.ascontiguousarray(image)


def to_bgr(image: np.ndarray) -> np.ndarray:
    """Return an independent BGR image; annotations never mutate caller input."""
    image = validate_image(image)
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image.copy()


def to_gray(image: np.ndarray) -> np.ndarray:
    image = validate_image(image)
    if image.ndim == 2:
        return image.copy()
    conversion = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
    return cv2.cvtColor(image, conversion)


def decode_image(data: bytes) -> np.ndarray:
    """Decode file/upload bytes by content, not by filename extension."""
    if not isinstance(data, bytes) or not data:
        raise InvalidImageError("Dữ liệu ảnh trống hoặc không phải bytes.")
    try:
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    except cv2.error as exc:
        raise InvalidImageError("Không giải mã được dữ liệu ảnh.") from exc
    if image is None:
        raise InvalidImageError("Dữ liệu không phải ảnh hợp lệ hoặc định dạng không hỗ trợ.")
    return to_bgr(image)


def read_image(path: str | Path) -> np.ndarray:
    """Read PNG/JPEG/BMP and other OpenCV-supported 8-bit images, in BGR order."""
    try:
        data = Path(path).read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        raise InvalidImageError(f"Không đọc được ảnh: {path}.") from exc
    return decode_image(data)
