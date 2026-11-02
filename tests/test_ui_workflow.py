"""Session lifecycle and error handling without a running Streamlit server."""

import cv2
import numpy as np
import pytest

from tests.synthetic import BOARD, make_scene
from tests.camera_fixtures import known_calibration
from visiongauge.ui.workflow import MeasurementWorkflow


def encoded_scene(**kwargs):
    ok, encoded = cv2.imencode(".png", make_scene(**kwargs).image)
    assert ok
    return encoded.tobytes()


def prepare(data=None, **kwargs):
    workflow = MeasurementWorkflow()
    workflow.update_input(
        encoded_scene() if data is None else data, BOARD, source="upload",
        image_geometry=kwargs.get("image_geometry", "undistorted"), segmentation="threshold",
    )
    return workflow


def test_measure_and_encode_download_without_mutating_image():
    workflow = prepare()
    before = workflow.image.copy()
    workflow.measure()
    assert workflow.result is not None
    assert workflow.result.length_mm == pytest.approx(65, abs=0.8)
    decoded = cv2.imdecode(np.frombuffer(workflow.result_png, np.uint8), cv2.IMREAD_COLOR)
    np.testing.assert_array_equal(decoded, workflow.result.annotated_image)
    np.testing.assert_array_equal(before, workflow.image)


def test_same_context_preserves_result_and_sessions_are_independent():
    data = encoded_scene()
    first, second = prepare(data), prepare(data)
    first.measure()
    old = first.result
    first.update_input(data, BOARD, source="upload", image_geometry="undistorted", segmentation="threshold")
    assert first.result is old
    assert second.result is None


def test_empty_image_is_not_treated_as_no_input():
    workflow = MeasurementWorkflow()
    for payload in (None, b""):
        workflow.update_input(payload, BOARD, source="upload", image_geometry=None, segmentation="threshold")
    assert workflow.input_error is not None


def test_measure_requires_distortion_declaration():
    workflow = prepare(image_geometry=None)
    workflow.measure()
    assert workflow.result is None
    assert "xác nhận" in workflow.measurement_error
    workflow.detect()
    assert workflow.detection is not None


def test_failed_measurement_keeps_board_preview():
    workflow = prepare(encoded_scene(include_product=False))
    workflow.measure()
    assert workflow.detection is not None
    assert workflow.board_preview is not None
    assert workflow.result_png is None
    assert "Không tìm thấy sản phẩm" in workflow.measurement_error


def test_repeat_detection_clears_download():
    workflow = prepare()
    workflow.measure()
    workflow.detect()
    assert workflow.detection is not None
    assert workflow.result is None
    assert workflow.result_png is None


def test_png_encoding_failure_does_not_publish_result(monkeypatch):
    workflow = prepare()
    monkeypatch.setattr("visiongauge.ui.workflow.cv2.imencode", lambda *args: (False, None))
    workflow.measure()
    assert workflow.result is None
    assert workflow.result_png is None
    assert "PNG" in workflow.measurement_error


def test_opencv_failure_is_readable(monkeypatch):
    workflow = prepare()

    def fail(*args):
        raise cv2.error("synthetic failure")

    monkeypatch.setattr("visiongauge.ui.workflow.detect_chessboard", fail)
    workflow.detect()
    assert workflow.detection is None
    assert "OpenCV" in workflow.board_error


def test_replacing_active_calibration_invalidates_measurement():
    data = encoded_scene()
    workflow = MeasurementWorkflow()
    workflow.update_input(data, BOARD, source="upload", image_geometry="calibrated", segmentation="threshold", calibration=known_calibration())
    workflow.measure()
    assert workflow.result is not None
    old_id = workflow.calibration_id
    workflow.update_input(data, BOARD, source="upload", image_geometry="calibrated", segmentation="threshold",
                          calibration=known_calibration(distortion=[-.05, 0, 0, 0, 0]))
    assert workflow.result is None
    assert workflow.result_png is None
    assert workflow.calibration_id != old_id


def test_calibrated_mode_requires_active_model():
    workflow = MeasurementWorkflow()
    workflow.update_input(encoded_scene(), BOARD, source="upload", image_geometry="calibrated", segmentation="threshold")
    assert workflow.image is None
    assert workflow.raw_image is not None
    assert "Chưa có calibration" in workflow.input_error
