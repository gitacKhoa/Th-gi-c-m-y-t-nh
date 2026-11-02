"""Actual upload/camera widgets + real OpenCV pipeline through Streamlit AppTest."""

from unittest.mock import patch

import cv2
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from tests.synthetic import make_scene
from visiongauge.config import ConfigurationError, PROJECT_ROOT


def start_app():
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    return app


def configure_board(app):
    app.number_input(key="board_columns").set_value(7)
    app.number_input(key="board_rows").set_value(5)
    app.number_input(key="square_size").set_value(10.0)
    app.selectbox(key="image_geometry").set_value("Ảnh đã khử méo / ảnh tổng hợp")
    return app.run()


def upload(app, **scene_options):
    ok, encoded = cv2.imencode(".png", make_scene(**scene_options).image)
    assert ok
    return app.file_uploader(key="uploaded_image").set_value(("ảnh sản phẩm.png", encoded.tobytes(), "image/png")).run()


def measured_app():
    app = upload(configure_board(start_app()), angle=23, perspective=1)
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert app.session_state["measurement_workflow"].result is not None
    return app


def test_empty_app_and_configuration():
    app = start_app()
    assert app.title[0].value == "VisionGauge"
    assert app.button(key="detect_board").disabled
    assert app.button(key="start_measurement").disabled
    assert [metric.value for metric in app.metric] == ["—", "—"]
    assert not app.download_button
    configure_board(app)
    assert not app.exception
    assert any("7 × 5" in item.value for item in app.caption)


def test_upload_detect_measure_debug_and_download():
    app = upload(configure_board(start_app()), angle=57, perspective=2)
    assert not app.exception
    assert not app.button(key="detect_board").disabled
    app.button(key="detect_board").click().run()
    workflow = app.session_state["measurement_workflow"]
    assert workflow.detection is not None
    assert len(workflow.detection.corners_px) == 35
    assert workflow.board_preview is not None
    assert workflow.result is None
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert not app.error
    assert float(app.metric[0].value) == pytest.approx(65, abs=0.8)
    assert float(app.metric[1].value) == pytest.approx(35, abs=0.8)
    assert len(app.download_button) == 1
    workflow = app.session_state["measurement_workflow"]
    decoded = cv2.imdecode(np.frombuffer(workflow.result_png, dtype=np.uint8), cv2.IMREAD_COLOR)
    np.testing.assert_array_equal(decoded, workflow.result.annotated_image)
    previous_result = workflow.result
    app.toggle(key="show_debug").set_value(True).run()
    assert not app.exception
    assert len(app.dataframe) == 2
    assert app.session_state["measurement_workflow"].result is previous_result
    app.download_button[0].click().run()
    assert not app.exception
    assert app.session_state["measurement_workflow"].result is previous_result


def test_camera_capture_widget_to_real_measurement():
    app = configure_board(start_app())
    app.radio(key="image_source").set_value("Chụp camera").run()
    assert len(app.camera_input) == 1
    assert app.camera_input(key="camera_image").proto.resolution_height == 720
    assert not app.file_uploader
    assert app.button(key="start_measurement").disabled
    _, encoded = cv2.imencode(".jpg", make_scene(angle=23, perspective=1).image)
    app.camera_input(key="camera_image").set_value(("capture.jpg", encoded.tobytes(), "image/jpeg")).run()
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert float(app.metric[0].value) == pytest.approx(65, abs=0.8)
    assert len(app.download_button) == 1


def test_detection_allowed_but_measure_disabled_without_geometry():
    app = upload(configure_board(start_app()))
    app.selectbox(key="image_geometry").set_value("Chưa xác nhận").run()
    assert app.button(key="start_measurement").disabled
    app.button(key="detect_board").click().run()
    assert app.session_state["measurement_workflow"].detection is not None
    assert not app.download_button


@pytest.mark.parametrize("change", ["columns", "rows", "size", "geometry", "segmentation", "source", "image", "remove"])
def test_changed_inputs_invalidate_all_old_results(change):
    app = measured_app()
    if change == "columns":
        app.number_input(key="board_columns").set_value(8).run()
    elif change == "rows":
        app.number_input(key="board_rows").set_value(6).run()
    elif change == "size":
        app.number_input(key="square_size").set_value(20.0).run()
    elif change == "geometry":
        app.selectbox(key="image_geometry").set_value("Chưa xác nhận").run()
    elif change == "segmentation":
        app.selectbox(key="segmentation").set_value("Canny").run()
    elif change == "source":
        app.radio(key="image_source").set_value("Chụp camera").run()
    elif change == "image":
        upload(app, angle=57)
    else:
        app.file_uploader(key="uploaded_image").clear().run()
    assert not app.exception
    workflow = app.session_state["measurement_workflow"]
    assert workflow.result is None
    assert workflow.result_png is None
    assert workflow.board_preview is None
    assert [metric.value for metric in app.metric] == ["—", "—"]
    assert not app.download_button


@pytest.mark.parametrize("options, message", [
    ({"include_board": False}, "Không tìm đủ"),
    ({"occlude_board": True}, "Không tìm đủ"),
    ({"include_product": False}, "Không tìm thấy sản phẩm"),
    ({"second_product": True}, "sản phẩm ứng viên"),
])
def test_readable_errors_after_upload(options, message):
    app = upload(configure_board(start_app()), **options)
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert any(message in item.value for item in app.error)
    assert not app.download_button
    assert [metric.value for metric in app.metric] == ["—", "—"]
    app.toggle(key="show_debug").set_value(True).run()
    assert not app.exception
    if options.get("include_product") is False:
        assert len(app.dataframe) == 2  # Corners and homography remain inspectable on failure.


def test_corrupt_upload_clears_previous_success():
    app = measured_app()
    app.file_uploader(key="uploaded_image").set_value(("broken.png", b"not an image", "image/png")).run()
    assert not app.exception
    assert any("ảnh hợp lệ" in item.value for item in app.error)
    assert app.button(key="start_measurement").disabled
    assert not app.download_button


def test_configuration_file_error_clears_session():
    app = measured_app()
    with patch("visiongauge.ui.app.load_config", side_effect=ConfigurationError("test error")):
        app.run()
    assert not app.exception
    assert "Lỗi cấu hình" in app.error[0].value
    assert app.session_state["measurement_workflow"].result is None
    assert not app.download_button


def test_invalid_square_size_clears_session():
    app = measured_app()
    app.number_input(key="square_size").set_value(0.0).run()
    assert not app.exception
    assert "Thông số bàn cờ không hợp lệ" in app.error[0].value
    assert app.session_state["measurement_workflow"].result is None
    assert not app.download_button


def test_canny_choice_reaches_pipeline():
    app = upload(configure_board(start_app()))
    app.selectbox(key="segmentation").set_value("Canny").run()
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert app.session_state["measurement_workflow"].segmentation == "canny"
    assert float(app.metric[1].value) == pytest.approx(35, abs=0.8)
