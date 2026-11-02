import os
import subprocess
import sys

import cv2
import numpy as np
import pytest

from visiongauge.__main__ import main
from visiongauge.config import PROJECT_ROOT
from visiongauge.errors import (
    AmbiguousProductError, CalibrationRequiredError, ChessboardNotFoundError,
    ProductNotFoundError, UnreliableMeasurementError,
)
from visiongauge.measurement import RectangleOptions, fit_metric_rectangle, measure_rectangle
from visiongauge.processing import ContourOptions
from tests.synthetic import BOARD, LENGTH_MM, WIDTH_MM, make_scene


@pytest.mark.parametrize("method", ["threshold", "canny"])
@pytest.mark.parametrize("perspective", [0, 1, 2])
@pytest.mark.parametrize("angle", [0, 23, 57, 90])
def test_measure_rotated_rectangle_under_perspective(angle, perspective, method):
    scene = make_scene(angle, perspective)
    result = measure_rectangle(
        scene.image, BOARD, image_geometry="undistorted",
        contour_options=ContourOptions(method=method),
    )
    assert result.length_mm == pytest.approx(LENGTH_MM, abs=0.8)
    assert result.width_mm == pytest.approx(WIDTH_MM, abs=0.8)
    assert result.length_mm >= result.width_mm > 0
    assert result.mapping.quality.rmse_px < 0.6
    assert result.corners_px.shape == (4, 2)
    assert result.annotated_image.shape == scene.image.shape
    assert result.segmentation_mask.shape == scene.image.shape[:2]
    assert not np.array_equal(result.annotated_image, scene.image)


@pytest.mark.parametrize("extra", [{"noise": True}, {"bright_product": True}])
def test_noise_and_bright_product(extra):
    scene = make_scene(angle=23, perspective=1, **extra)
    before = scene.image.copy()
    result = measure_rectangle(scene.image, BOARD, image_geometry="undistorted")
    assert result.length_mm == pytest.approx(LENGTH_MM, abs=0.8)
    assert result.width_mm == pytest.approx(WIDTH_MM, abs=0.8)
    np.testing.assert_array_equal(before, scene.image)


@pytest.mark.parametrize("extra", [
    {"include_product": False}, {"product_shape": "circle"},
    {"product_shape": "trapezoid"}, {"product_center": (220, 95)},
    {"product_center": (98, 95)},
])
def test_reject_absent_nonrectangular_cutoff_or_board_touching_product(extra):
    with pytest.raises(ProductNotFoundError):
        measure_rectangle(make_scene(**extra).image, BOARD, image_geometry="undistorted")


def test_multiple_products_are_ambiguous():
    with pytest.raises(AmbiguousProductError):
        measure_rectangle(make_scene(second_product=True).image, BOARD, image_geometry="undistorted")


def test_unmappable_large_contour_is_not_silently_replaced_by_another_object():
    scene = make_scene(product_center=(190, 95), second_product=True)
    with pytest.raises(UnreliableMeasurementError, match="ánh xạ"):
        measure_rectangle(scene.image, BOARD, image_geometry="undistorted")


@pytest.mark.parametrize("extra", [{"include_board": False}, {"occlude_board": True}])
def test_pipeline_never_returns_measurements_without_complete_board(extra):
    with pytest.raises(ChessboardNotFoundError):
        measure_rectangle(make_scene(**extra).image, BOARD, image_geometry="undistorted")


def test_distortion_assumption_must_be_explicit():
    scene = make_scene()
    with pytest.raises(CalibrationRequiredError):
        measure_rectangle(scene.image, BOARD)
    result = measure_rectangle(scene.image, BOARD, image_geometry="negligible_distortion")
    assert any("méo ống kính" in warning for warning in result.warnings)


def test_metric_geometry_exact_rotated_rectangle():
    contour = cv2.boxPoints(((40, 50), (65, 35), 37))
    result = fit_metric_rectangle(contour)
    assert result.length_mm == pytest.approx(65, abs=1e-4)
    assert result.width_mm == pytest.approx(35, abs=1e-4)


@pytest.mark.parametrize("contour", [
    [[0, 0], [1, 0], [0, 1]],
    [[0, 0], [0, 0], [0, 0], [0, 0]],
    [[0, 0], [65, 0], [45, 35], [10, 35]],
    [[0, 0], [65, 0], [float("nan"), 35], [0, 35]],
])
def test_reject_invalid_metric_geometry(contour):
    with pytest.raises(UnreliableMeasurementError):
        fit_metric_rectangle(np.array(contour, dtype=float))


@pytest.mark.parametrize("options", [
    {"blur_kernel": 4}, {"min_area_px": -1}, {"canny_low": 200, "canny_high": 100},
    {"method": "unknown"}, {"board_margin_squares": -1},
])
def test_reject_invalid_contour_options(options):
    with pytest.raises(ValueError):
        ContourOptions(**options)


def test_reject_invalid_rectangle_options():
    with pytest.raises(ValueError):
        RectangleOptions(min_rectangularity=1.1)


def test_cli_success_and_error(tmp_path, capsys):
    path, output = tmp_path / "ảnh thử.png", tmp_path / "kết quả.png"
    _, encoded = cv2.imencode(".png", make_scene(23, 1).image)
    path.write_bytes(encoded.tobytes())
    args = [str(path), "--columns", "7", "--rows", "5", "--square-size-mm", "10",
            "--image-geometry", "undistorted", "--output", str(output)]
    assert main(args) == 0
    assert output.is_file()
    assert "Length:" in capsys.readouterr().out
    args[0] = str(tmp_path / "missing.png")
    assert main(args) == 2
    assert "KHÔNG THỂ ĐÁNH GIÁ" in capsys.readouterr().err


@pytest.mark.parametrize("valid_image", [True, False])
def test_cli_real_process_handles_legacy_windows_encoding(tmp_path, valid_image):
    path = tmp_path / "input.png"
    if valid_image:
        _, encoded = cv2.imencode(".png", make_scene().image)
        path.write_bytes(encoded.tobytes())
    completed = subprocess.run(
        [sys.executable, "-m", "visiongauge", str(path), "--columns", "7", "--rows", "5",
         "--square-size-mm", "10", "--image-geometry", "undistorted"],
        cwd=PROJECT_ROOT, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert completed.returncode == (0 if valid_image else 2)
    if valid_image:
        assert "Length:" in completed.stdout
        assert "độ chính xác thực nghiệm" in completed.stdout
    else:
        assert "KHÔNG THỂ ĐÁNH GIÁ" in completed.stderr
