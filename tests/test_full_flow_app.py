"""Full UI integration using isolated history and explicitly synthetic fixtures."""

import cv2
import pytest
from streamlit.testing.v1 import AppTest

from tests.camera_fixtures import known_calibration
from tests.synthetic import make_scene
from tests.test_full_flow import image_bytes
from visiongauge.calibration import calibration_to_json
from visiongauge.config import PROJECT_ROOT
from visiongauge.storage import HistoryStore, HistoryError


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "ui_history.sqlite3"
    monkeypatch.setenv("VISIONGAUGE_HISTORY_DB", str(path))
    return path


def start_flow():
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=40).run()
    app.radio(key="app_page").set_value("Quy trình đo").run()
    assert not app.exception
    app.number_input(key="flow_columns").set_value(7)
    app.number_input(key="flow_rows").set_value(5)
    app.number_input(key="flow_square").set_value(10.)
    app.text_input(key="flow_product").set_value("UI-TEST-ONLY")
    app.checkbox(key="flow_conditions").set_value(True)
    for dimension, nominal in (("length", 65.), ("width", 35.)):
        app.number_input(key=f"tolerance_{dimension}_nominal").set_value(nominal)
        app.number_input(key=f"tolerance_{dimension}_lower").set_value(-1.)
        app.number_input(key=f"tolerance_{dimension}_upper").set_value(1.)
    return app.run()


def load_model(app, model=None):
    data = calibration_to_json(model or known_calibration())
    return app.file_uploader(key="flow_calibration").set_value(("fixture_calibration.json", data, "application/json")).run()


def upload_batch(app, bad=True):
    files = [("synthetic-software-test.png", image_bytes(), "image/png")]
    if bad:
        files.append(("invalid.png", b"invalid", "image/png"))
    return app.file_uploader(key="flow_images").set_value(files).run()


def run(app):
    app.button(key="run_full_flow").click().run()
    assert not app.exception
    return app


def test_upload_calibration_batch_history_detail_and_reports(database):
    app = run(upload_batch(load_model(start_flow())))
    store = HistoryStore(database)
    records = store.list_records()
    assert len(records) == 2
    assert {r["decision"] for r in records} == {"ĐẠT", "KHÔNG THỂ ĐÁNH GIÁ"}
    assert not app.session_state["flow_pending"]
    app.run()
    assert len(store.list_records()) == 2  # Reruns do not create measurements.
    app.radio(key="app_page").set_value("Lịch sử").run()
    assert not app.exception
    assert [m.value for m in app.metric[:3]] == ["1", "0", "1"]
    app.button(key="history_create_pdf").click().run()
    assert not app.exception
    assert app.download_button(key="history_pdf_download")
    app.selectbox(key="history_status").set_value("ĐẠT").run()
    assert not any(button.key == "history_pdf_download" for button in app.download_button)
    assert [m.value for m in app.metric[:3]] == ["1", "0", "0"]
    app.button(key="history_detail_pdf").click().run()
    assert not app.exception
    assert app.download_button(key="history_detail_pdf_download")
    assert app.download_button(key="history_selected_png")
    app.download_button(key="history_csv").click().run()
    assert len(store.list_records()) == 2
    # A separate browser session reads persisted records, not session state.
    another = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30).run()
    another.radio(key="app_page").set_value("Lịch sử").run()
    assert not another.exception
    assert [m.value for m in another.metric[:3]] == ["1", "0", "1"]


@pytest.mark.parametrize("fault,code", [
    ("missing", "MISSING_CALIBRATION"), ("json", "INVALID_CALIBRATION"),
    ("size", "RESOLUTION_MISMATCH"), ("conditions", "CONDITIONS_UNCONFIRMED"),
    ("specification", "INVALID_CONFIGURATION"),
])
def test_failed_prerequisites_are_saved_as_unknown(database, fault, code):
    app = start_flow()
    if fault != "missing":
        load_model(app, known_calibration((640, 480)) if fault == "size" else None)
    if fault == "json":
        # Invalid uploaded JSON must not fall back to a prior active model.
        app.session_state["active_calibration"] = known_calibration()
        app.file_uploader(key="flow_calibration").set_value(("bad.json", b"{}", "application/json")).run()
    if fault == "conditions":
        app.checkbox(key="flow_conditions").set_value(False).run()
    if fault == "specification":
        app.number_input(key="tolerance_width_nominal").set_value(None).run()
    run(upload_batch(app, bad=False))
    record = HistoryStore(database).list_records()[0]
    assert record["decision"] == "KHÔNG THỂ ĐÁNH GIÁ"
    assert record["error_code"] == code
    assert not any(button.key == "flow_detail_png" for button in app.download_button)


@pytest.mark.parametrize("change", ["board", "spec", "calibration", "image", "source", "conditions"])
def test_changed_input_hides_old_result_but_preserves_saved_snapshot(database, change):
    app = run(upload_batch(load_model(start_flow()), bad=False))
    original = HistoryStore(database).list_records()[0]
    if change == "board":
        app.number_input(key="flow_square").set_value(20.).run()
    elif change == "spec":
        app.number_input(key="tolerance_length_upper").set_value(0.).run()
    elif change == "calibration":
        app.file_uploader(key="flow_calibration").clear().run()
    elif change == "image":
        app.file_uploader(key="flow_images").clear().run()
    elif change == "source":
        app.segmented_control(key="flow_source").set_value("Camera").run()
    else:
        app.checkbox(key="flow_conditions").set_value(False).run()
    assert not app.exception
    assert not any(button.key == "flow_detail_png" for button in app.download_button)
    assert any("Đầu vào đã thay đổi" in element.value for element in app.info)
    assert HistoryStore(database).list_records() == [original]


def test_camera_successive_measurements_have_independent_ids(database):
    app = load_model(start_flow())
    app.segmented_control(key="flow_source").set_value("Camera").run()
    for angle in (0, 23):
        payload = cv2.imencode(".jpg", make_scene(angle=angle).image)[1].tobytes()
        app.camera_input(key="flow_camera").set_value(("camera.jpg", payload, "image/jpeg")).run()
        run(app)
    rows = HistoryStore(database).list_records()
    assert len(rows) == 2
    assert len({r["run_id"] for r in rows}) == 2
    assert all(r["source"] == "camera" and r["decision"] == "ĐẠT" for r in rows)


def test_storage_failure_retains_unsaved_outcome_and_retry_does_not_remeasure(database, monkeypatch):
    app = upload_batch(load_model(start_flow()), bad=False)
    real_save = HistoryStore.save

    def fail(*args, **kwargs):
        raise HistoryError("test write failure")

    monkeypatch.setattr(HistoryStore, "save", fail)
    run(app)
    assert len(app.session_state["flow_pending"]) == 1
    original = app.session_state["flow_pending"][0]
    assert any("LỖI LƯU TRỮ" in element.value for element in app.error)
    assert app.button(key="run_full_flow").disabled
    monkeypatch.setattr(HistoryStore, "save", real_save)
    app.button(key="retry_history").click().run()
    assert not app.exception
    assert not app.session_state["flow_pending"]
    assert HistoryStore(database).get(original.record["run_id"]) == original
    app.run()
    assert len(HistoryStore(database).list_records()) == 1


def test_active_calibration_from_calibration_page_is_used(database):
    app = start_flow()
    app.session_state["active_calibration"] = known_calibration()
    run(upload_batch(app, bad=False))
    record = HistoryStore(database).list_records()[0]
    assert record["calibration_id"] == known_calibration().fingerprint
    assert record["decision"] == "ĐẠT"


def test_history_storage_error_is_visible_without_crashing(database):
    database.write_text("not a sqlite database")
    app = start_flow()
    app.radio(key="app_page").set_value("Lịch sử").run()
    assert not app.exception
    assert any("LỖI ĐỌC LỊCH SỬ" in element.value for element in app.error)
