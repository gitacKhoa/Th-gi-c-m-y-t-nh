import cv2
import numpy as np
import pytest

from visiongauge.errors import InvalidImageError
from visiongauge.image_io import decode_image, read_image, to_bgr, to_gray, validate_image


@pytest.mark.parametrize("image", [
    None, [], np.zeros((0, 20), dtype=np.uint8), np.zeros((20, 0), dtype=np.uint8),
    np.zeros((20, 20), dtype=np.float32), np.zeros((20, 20), dtype=np.uint16),
    np.zeros((20, 20, 1), dtype=np.uint8), np.zeros((20, 20, 2), dtype=np.uint8),
    np.zeros((20, 20, 3, 2), dtype=np.uint8), np.zeros((20, 20, 4), dtype=np.uint8),
])
def test_reject_invalid_images(image):
    with pytest.raises(InvalidImageError):
        validate_image(image)


@pytest.mark.parametrize("data", [b"", b"not an image", None, "abc"])
def test_reject_invalid_encoded_image(data):
    with pytest.raises(InvalidImageError):
        decode_image(data)


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".bmp"])
def test_unicode_path_and_content_decoding(tmp_path, suffix):
    image = np.full((40, 50, 3), 120, dtype=np.uint8)
    ok, data = cv2.imencode(suffix, image)
    assert ok
    path = tmp_path / "ảnh sản phẩm.unknown"
    path.write_bytes(data.tobytes())
    decoded = read_image(path)
    assert decoded.shape == image.shape
    np.testing.assert_allclose(decoded, image, atol=1)


def test_missing_image(tmp_path):
    with pytest.raises(InvalidImageError, match="Không đọc được"):
        read_image(tmp_path / "missing.png")


def test_gray_bgra_and_noncontiguous_inputs():
    gray = np.full((40, 50), 100, dtype=np.uint8)
    np.testing.assert_array_equal(to_gray(to_bgr(gray)), gray)
    bgra = cv2.cvtColor(to_bgr(gray), cv2.COLOR_BGR2BGRA)
    np.testing.assert_array_equal(to_bgr(bgra), to_bgr(gray))
    assert validate_image(gray[:, ::-1]).flags.c_contiguous
    assert not np.shares_memory(to_bgr(gray), gray)


def test_uint16_file_is_not_silently_scaled():
    _, encoded = cv2.imencode(".png", np.full((20, 20), 1024, dtype=np.uint16))
    with pytest.raises(InvalidImageError):
        decode_image(encoded.tobytes())
