"""Calibration UI, persistence, application and paired-evaluation workflows."""

from dataclasses import replace

import cv2
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from tests.camera_fixtures import known_calibration, rendered_calibration_images
from tests.synthetic import make_scene
from visiongauge.calibration import calibration_to_json, undistort_image
from visiongauge.config import PROJECT_ROOT


def calibration_page():
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=90).run()
    app.radio(key="app_page").set_value("Camera Calibration").run()
    app.number_input(key="cal_columns").set_value(7)
    app.number_input(key="cal_rows").set_value(5)
    app.number_input(key="cal_square_size").set_value(20.0)
    app.run()
    assert not app.exception
    return app


def load_and_apply(app, model=None):
    model = model or known_calibration()
    app.file_uploader(key="calibration_json").set_value(("synthetic_model.json", calibration_to_json(model), "application/json")).run()
    app.button(key="load_calibration").click().run()
    assert not app.exception
    app.button(key="apply_loaded_calibration").click().run()
    assert app.session_state["active_calibration"].fingerprint == model.fingerprint
    return app


def measurement_page(app):
    app.radio(key="app_page").set_value("Đo kích thước").run()
    app.number_input(key="board_columns").set_value(7)
    app.number_input(key="board_rows").set_value(5)
    app.number_input(key="square_size").set_value(10.)
    app.run()
    assert app.selectbox(key="image_geometry").value == "Dùng calibration đang áp dụng"
    return app


def test_camera_page_fits_downloads_and_invalidates_changed_dataset():
    app = calibration_page()
    assert app.button(key="fit_calibration").disabled
    images = list(rendered_calibration_images())
    app.file_uploader(key="calibration_images").set_value([(name, data, "image/png") for name, data in images]).run()
    app.button(key="scan_calibration").click().run()
    assert not app.exception
    assert len(app.session_state["calibration_workflow"].scan.views) == 12
    app.button(key="fit_calibration").click().run()
    assert not app.exception
    assert not app.error
    result = app.session_state["calibration_workflow"].result
    assert result.rms_px < .6
    assert app.download_button(key="download_generated_calibration") is not None
    app.button(key="apply_generated_calibration").click().run()
    assert app.session_state["active_calibration"].fingerprint == result.fingerprint
    app.number_input(key="cal_square_size").set_value(21.).run()
    assert app.session_state["calibration_workflow"].result is None
    assert not any(button.key == "download_generated_calibration" for button in app.download_button)


def test_too_few_good_images_are_reported():
    app = calibration_page()
    name, data = rendered_calibration_images()[0]
    app.file_uploader(key="calibration_images").set_value([(name, data, "image/png"), ("bad.png", b"bad", "image/png")]).run()
    app.button(key="fit_calibration").click().run()
    assert not app.exception
    assert any("ít nhất 5" in error.value for error in app.error)
    scan = app.session_state["calibration_workflow"].scan
    assert len(scan.views) == len(scan.failures) == 1


def test_bad_board_and_bad_json_are_readable():
    app = calibration_page()
    app.number_input(key="cal_square_size").set_value(0.).run()
    assert any("không hợp lệ" in item.value for item in app.error)
    app.number_input(key="cal_square_size").set_value(20.).run()
    app.file_uploader(key="calibration_json").set_value(("bad.json", b"{}", "application/json")).run()
    app.button(key="load_calibration").click().run()
    assert not app.exception
    assert any("Không nạp được" in item.value for item in app.error)
    assert "active_calibration" not in app.session_state


def test_loaded_calibration_is_applied_once_before_detection_and_measurement():
    model = known_calibration(distortion=[-.1, .02, .0005, 0, 0])
    app = measurement_page(load_and_apply(calibration_page(), model))
    ideal = make_scene(23, 1).image
    yy, xx = np.indices(ideal.shape[:2], dtype=np.float32)
    raw_pixels = np.column_stack((xx.ravel(), yy.ravel())).reshape(-1, 1, 2)
    ideal_pixels = cv2.undistortPoints(raw_pixels, model.camera_matrix, model.distortion, P=model.camera_matrix).reshape(*ideal.shape[:2], 2)
    raw = cv2.remap(ideal, ideal_pixels[:, :, 0], ideal_pixels[:, :, 1], cv2.INTER_LINEAR, borderValue=(230, 230, 230))
    _, encoded = cv2.imencode(".png", raw)
    app.file_uploader(key="uploaded_image").set_value(("synthetic_distorted.png", encoded.tobytes(), "image/png")).run()
    app.button(key="start_measurement").click().run()
    assert not app.exception
    workflow = app.session_state["measurement_workflow"]
    assert workflow.result is not None, workflow.measurement_error or workflow.board_error
    np.testing.assert_array_equal(workflow.raw_image, raw)
    np.testing.assert_array_equal(workflow.image, undistort_image(raw, model))
    assert workflow.result.length_mm == pytest.approx(65, abs=.8)
    previous_image = workflow.image.copy()
    app.toggle(key="show_debug").set_value(True).run()
    np.testing.assert_array_equal(app.session_state["measurement_workflow"].image, previous_image)


def test_resolution_mismatch_disables_measurement():
    app = measurement_page(load_and_apply(calibration_page(), known_calibration((640, 480))))
    _, encoded = cv2.imencode(".png", make_scene().image)
    app.file_uploader(key="uploaded_image").set_value(("wrong_size.png", encoded.tobytes(), "image/png")).run()
    assert not app.exception
    assert any("độ phân giải" in item.value for item in app.error)
    assert app.button(key="start_measurement").disabled
    assert not app.download_button


def test_comparison_ui_without_truth_then_with_reference_csv():
    app = load_and_apply(calibration_page())
    app.number_input(key="cal_square_size").set_value(10.).run()
    _, encoded = cv2.imencode(".png", make_scene(23, 1).image)
    app.file_uploader(key="comparison_images").set_value([("synthetic.png", encoded.tobytes(), "image/png")]).run()
    app.button(key="run_comparison").click().run()
    assert not app.exception
    assert any("Chưa có đủ cặp" in item.value for item in app.info)
    assert app.download_button(key="download_comparison") is not None
    app.file_uploader(key="comparison_reference").set_value(("reference.csv", b"filename,length_mm,width_mm\nsynthetic.png,65,35\n", "text/csv")).run()
    assert "comparison_table" not in app.session_state
    app.button(key="run_comparison").click().run()
    assert not app.exception
    table = app.session_state["comparison_table"]
    assert table.loc[0, "reference_length_mm"] == 65


def test_removing_calibration_clears_active_model():
    app = load_and_apply(calibration_page())
    app.run()
    app.button(key="clear_calibration").click().run()
    assert not app.exception
    assert "active_calibration" not in app.session_state


def test_loaded_model_above_quality_threshold_cannot_be_applied():
    app = calibration_page()
    model = replace(known_calibration(), rms_px=3., per_view_rmse_px=np.full(5, 3.))
    app.file_uploader(key="calibration_json").set_value(("bad_fit.json", calibration_to_json(model), "application/json")).run()
    app.button(key="load_calibration").click().run()
    assert not app.exception
    assert app.button(key="apply_loaded_calibration").disabled
    assert any("vượt ngưỡng" in item.value for item in app.warning)


@pytest.mark.parametrize("size, requested_height", [((640, 480), 480), ((1280, 720), 720), ((1920, 1080), 1080), ((900, 640), 720)])
def test_camera_requests_calibration_height_and_rejects_mismatched_capture(size, requested_height):
    app = measurement_page(load_and_apply(calibration_page(), known_calibration(size)))
    app.radio(key="image_source").set_value("Chụp camera").run()
    assert app.camera_input(key="camera_image").proto.resolution_height == requested_height
    assert any(f"{size[0]} × {size[1]}" in item.value for item in app.info)
    # Reproduce the user's display-sized capture. Do not silently resize it.
    raw = np.full((584, 778, 3), 200, dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", raw)
    app.camera_input(key="camera_image").set_value(("capture.jpg", encoded.tobytes(), "image/jpeg")).run()
    assert not app.exception
    workflow = app.session_state["measurement_workflow"]
    np.testing.assert_array_equal(workflow.raw_image, cv2.imdecode(encoded, cv2.IMREAD_COLOR))
    assert workflow.image is None
    assert app.button(key="start_measurement").disabled
    assert any("Ảnh đọc được" in item.value for item in app.warning)
    assert not app.download_button
