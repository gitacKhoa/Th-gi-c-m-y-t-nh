from dataclasses import replace
import json

import cv2
import numpy as np
import pytest

from tests.camera_fixtures import (
    CAMERA_BOARD, CAMERA_D, CAMERA_K, CAMERA_SIZE, POSES, known_calibration, projected_views, rendered_calibration_images, rendered_product_image,
)
from visiongauge.calibration import (
    calibrate_camera, calibration_from_json, calibration_to_json, chessboard_points_mm,
    estimate_planar_mapping, load_calibration, save_calibration, scan_calibration_images,
    undistort_image, undistort_image_points,
)
from visiongauge.errors import CameraCalibrationError
from visiongauge.measurement import measure_rectangle


def test_recover_known_camera_and_extrinsics_from_synthetic_coordinates():
    result = calibrate_camera(projected_views(), CAMERA_BOARD)
    np.testing.assert_allclose(result.camera_matrix, CAMERA_K, atol=.03)
    np.testing.assert_allclose(result.distortion, CAMERA_D, atol=.005)
    assert result.rms_px < 1e-3
    assert result.rvecs.shape == result.tvecs.shape == (12, 3)
    np.testing.assert_allclose(result.tvecs, [pose[1] for pose in POSES], atol=.05)
    assert result.rms_px == pytest.approx(np.sqrt(np.mean(result.per_view_rmse_px ** 2)))


def test_detect_and_calibrate_rendered_distorted_chessboards():
    scan = scan_calibration_images(list(rendered_calibration_images()), CAMERA_BOARD)
    assert not scan.failures
    assert len(scan.views) == 12
    result = calibrate_camera(scan.views, CAMERA_BOARD)
    assert result.rms_px < .6
    np.testing.assert_allclose(result.camera_matrix[:2, :2], CAMERA_K[:2, :2], atol=15)
    corrected = undistort_image(rendered_product_image(), result)
    measured = measure_rectangle(corrected, CAMERA_BOARD, image_geometry="undistorted")
    assert measured.length_mm == pytest.approx(65, abs=.8)
    assert measured.width_mm == pytest.approx(35, abs=.8)


@pytest.mark.parametrize("count", [0, 1, 4])
def test_too_few_views(count):
    with pytest.raises(CameraCalibrationError, match="ít nhất 5"):
        calibrate_camera(projected_views()[:count], CAMERA_BOARD)


def test_reject_same_pose_and_bad_observations():
    views = projected_views()
    duplicates = tuple(replace(views[0], name=str(i)) for i in range(5))
    with pytest.raises(CameraCalibrationError, match="đa dạng"):
        calibrate_camera(duplicates, CAMERA_BOARD)
    for broken in (replace(views[0], image_size=(320, 240)), replace(views[0], corners_px=np.zeros((4, 2)))):
        with pytest.raises(CameraCalibrationError):
            calibrate_camera((broken,) + views[1:], CAMERA_BOARD)


def test_high_reprojection_error_is_rejected():
    with pytest.raises(CameraCalibrationError, match="ngưỡng"):
        calibrate_camera(projected_views(noise=3), CAMERA_BOARD)


def test_scan_reports_failure_duplicate_and_resolution():
    images = list(rendered_calibration_images()[:1])
    _, blank = cv2.imencode(".png", np.full((480, 640), 255, np.uint8))
    _, small = cv2.imencode(".png", np.full((240, 320), 255, np.uint8))
    images += [("duplicate.png", images[0][1]), ("blank.png", blank.tobytes()),
               ("small.png", small.tobytes()), ("broken.png", b"bad")]
    scan = scan_calibration_images(images, CAMERA_BOARD)
    assert len(scan.views) == 1
    assert len(scan.failures) == 4
    assert "trùng" in dict(scan.failures)["duplicate.png"]
    assert "độ phân giải" in dict(scan.failures)["small.png"]


def test_json_roundtrip_unicode_path(tmp_path):
    original = known_calibration()
    path = tmp_path / "hiệu chuẩn.json"
    save_calibration(path, original)
    loaded = load_calibration(path)
    assert loaded.fingerprint == original.fingerprint
    np.testing.assert_array_equal(loaded.camera_matrix, original.camera_matrix)
    assert not loaded.camera_matrix.flags.writeable


@pytest.mark.parametrize("change", ["matrix", "nan", "size", "schema", "model", "views", "rmse", "board"])
def test_invalid_json_models_rejected(change):
    payload = json.loads(calibration_to_json(known_calibration()))
    if change == "matrix":
        payload["camera_matrix"][0][0] = -1
    elif change == "nan":
        payload["distortion"][0] = float("nan")
    elif change == "size":
        payload["image_size"] = [640.5, 480]
    elif change == "schema":
        payload["schema_version"] = 2
    elif change == "model":
        payload["model"] = "fisheye"
    elif change == "views":
        payload["tvecs"] = []
    elif change == "rmse":
        payload["rms_px"] = 100
    else:
        payload["board"]["square_size_mm"] = -1
    with pytest.raises(CameraCalibrationError):
        calibration_from_json(json.dumps(payload).encode())


@pytest.mark.parametrize("data", [b"", b"[]", b"{}", b"not JSON"])
def test_malformed_json(data):
    with pytest.raises(CameraCalibrationError):
        calibration_from_json(data)


def test_undistortion_identity_resolution_and_no_mutation():
    model = known_calibration(CAMERA_SIZE)
    rng = np.random.default_rng(3)
    image = rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
    before = image.copy()
    corrected = undistort_image(image, model)
    np.testing.assert_array_equal(corrected, image)
    np.testing.assert_array_equal(image, before)
    with pytest.raises(CameraCalibrationError, match="độ phân giải"):
        undistort_image(image[:240], model)


def test_homography_uses_undistorted_pixel_coordinates():
    model = replace(known_calibration(CAMERA_SIZE), camera_matrix=CAMERA_K, distortion=CAMERA_D)
    world = chessboard_points_mm(CAMERA_BOARD)
    product_mm = np.array([[180, 0], [245, 0], [245, 35], [180, 35]], float)
    points = np.column_stack((np.vstack((world, product_mm)), np.zeros(len(world) + 4)))
    rotation, translation = np.array([.12, -.1, .04]), np.array([-60., -40., 500.])
    distorted, _ = cv2.projectPoints(points, rotation, translation, CAMERA_K, CAMERA_D)
    expected, _ = cv2.projectPoints(points, rotation, translation, CAMERA_K, np.zeros(5))
    corrected = undistort_image_points(distorted.reshape(-1, 2), model)
    np.testing.assert_allclose(corrected, expected.reshape(-1, 2), atol=1e-6)
    mapping = estimate_planar_mapping(corrected[:len(world)], CAMERA_BOARD)
    np.testing.assert_allclose(mapping.to_mm(corrected[-4:]), product_mm, atol=1e-3)


def test_reject_nonmonotonic_radial_model():
    with pytest.raises(CameraCalibrationError, match="đơn điệu"):
        replace(known_calibration(), distortion=np.array([-5., 0, 0, 0, 0]))
