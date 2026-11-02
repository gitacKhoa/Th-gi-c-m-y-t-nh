"""Browser-camera dataset collection and the real calibration pipeline."""

from io import BytesIO
from zipfile import ZipFile

import cv2
import numpy as np
import pytest

from tests.camera_fixtures import rendered_calibration_images
from tests.test_calibration_app import calibration_page
from visiongauge.errors import VisionGaugeError
from visiongauge.ui.capture_workflow import CalibrationCaptures


def jpeg(data):
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def camera_page():
    app = calibration_page()
    app.radio(key="calibration_source").set_value("Chụp camera").run()
    return app


def stage_and_add(app, data):
    app.camera_input[0].set_value(("capture.jpg", data, "image/jpeg")).run()
    app.button(key="add_calibration_capture").click().run()
    assert not app.exception


def test_capture_store_rejects_invalid_duplicate_and_mismatched_frames_and_preserves_bytes():
    store = CalibrationCaptures()
    payload = jpeg(rendered_calibration_images()[0][1])
    with pytest.raises(VisionGaugeError):
        store.add(b"not an image")
    assert not store.images
    name = store.add(payload)
    with pytest.raises(VisionGaugeError, match="đã được thêm"):
        store.add(payload)
    _, different_size = cv2.imencode(".jpg", np.zeros((120, 160, 3), dtype=np.uint8))
    with pytest.raises(VisionGaugeError, match="khác bộ ảnh"):
        store.add(different_size.tobytes())
    assert store.images == [(name, payload)]
    with ZipFile(BytesIO(store.archive())) as archive:
        assert archive.namelist() == [name]
        assert archive.read(name) == payload
    store.remove(name)
    assert store.image_size is None
    store.add(different_size.tobytes())
    assert store.image_size == (160, 120)
    store.clear()
    assert not store.images and store.image_size is None


def test_camera_collects_multiple_photos_fits_applies_and_invalidates_on_delete():
    app = camera_page()
    assert app.camera_input[0].proto.resolution_height == 720
    assert app.button(key="add_calibration_capture").disabled
    assert app.button(key="fit_calibration").disabled
    photos = [jpeg(data) for _, data in rendered_calibration_images()]
    for index, data in enumerate(photos):
        stage_and_add(app, data)
        assert len(app.session_state["calibration_captures"].images) == index + 1
        assert app.button(key="add_calibration_capture").disabled
    app.run()
    assert len(app.session_state["calibration_captures"].images) == 12
    assert app.selectbox(key="calibration_capture_resolution").disabled
    assert app.download_button(key="download_calibration_captures") is not None
    app.button(key="scan_calibration").click().run()
    assert len(app.session_state["calibration_workflow"].scan.views) == 12
    app.button(key="fit_calibration").click().run()
    assert not app.exception and not app.error
    result = app.session_state["calibration_workflow"].result
    assert result is not None and result.image_size == (640, 480)
    app.button(key="apply_generated_calibration").click().run()
    assert app.session_state["active_calibration"].fingerprint == result.fingerprint
    app.button(key="remove_calibration_capture").click().run()
    assert not app.exception
    assert len(app.session_state["calibration_captures"].images) == 11
    assert app.session_state["calibration_workflow"].result is None
    assert app.session_state["active_calibration"].fingerprint == result.fingerprint
    app.button(key="clear_calibration_captures").click().run()
    assert not app.exception
    assert not app.session_state["calibration_captures"].images
    assert app.button(key="fit_calibration").disabled
    assert not app.selectbox(key="calibration_capture_resolution").disabled


def test_camera_reports_failed_board_and_insufficient_images():
    app = camera_page()
    _, plain = cv2.imencode(".jpg", np.full((480, 640, 3), 230, dtype=np.uint8))
    stage_and_add(app, plain.tobytes())
    stage_and_add(app, jpeg(rendered_calibration_images()[0][1]))
    app.button(key="fit_calibration").click().run()
    assert not app.exception
    scan = app.session_state["calibration_workflow"].scan
    assert len(scan.views) == len(scan.failures) == 1
    assert any("ít nhất 5" in item.value for item in app.error)


def test_camera_frames_and_preset_survive_page_switch_and_configuration_changes():
    app = camera_page()
    app.selectbox(key="calibration_capture_resolution").set_value("480p").run()
    stage_and_add(app, jpeg(rendered_calibration_images()[0][1]))
    app.button(key="scan_calibration").click().run()
    assert app.session_state["calibration_workflow"].scan is not None
    app.number_input(key="cal_square_size").set_value(21.).run()
    assert app.session_state["calibration_workflow"].scan is None
    app.radio(key="app_page").set_value("Đo kích thước").run()
    app.radio(key="app_page").set_value("Camera Calibration").run()
    app.radio(key="calibration_source").set_value("Chụp camera").run()
    assert not app.exception
    assert len(app.session_state["calibration_captures"].images) == 1
    assert app.camera_input[0].proto.resolution_height == 480
    app.radio(key="calibration_source").set_value("Upload ảnh").run()
    assert app.button(key="fit_calibration").disabled
    app.radio(key="calibration_source").set_value("Chụp camera").run()
    assert not app.button(key="fit_calibration").disabled


def test_camera_capture_errors_do_not_modify_dataset():
    app = camera_page()
    stage_and_add(app, b"bad jpeg")
    assert app.error and not app.session_state["calibration_captures"].images
    photo = jpeg(rendered_calibration_images()[0][1])
    stage_and_add(app, photo)
    stage_and_add(app, photo)
    assert any("đã được thêm" in item.value for item in app.error)
    _, other = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))
    stage_and_add(app, other.tobytes())
    assert any("khác bộ ảnh" in item.value for item in app.error)
    assert len(app.session_state["calibration_captures"].images) == 1
