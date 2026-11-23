"""Integration fixtures are synthetic SOFTWARE TESTS, never experimental records."""

from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import cv2
import numpy as np
import pytest

from tests.camera_fixtures import (
    CAMERA_BOARD, known_calibration, rendered_calibration_images, rendered_product_image,
)
from tests.synthetic import BOARD, make_scene
from visiongauge.calibration import (
    calibrate_camera, scan_calibration_images, calibration_from_json, calibration_to_json, undistort_image,
)
from visiongauge.errors import UnreliableMappingError, UnreliableMeasurementError
from visiongauge.storage import HistoryStore, summarize_records
from visiongauge.tolerance import DimensionTolerance, ProductTolerance
from visiongauge.workflow import InspectionSettings, QualityOptions, check_image_quality, inspect_batch, inspect_image
from visiongauge.workflow.models import PASS, FAIL, NOT_EVALUABLE
import visiongauge.workflow.service as service


def image_bytes(**options):
    return cv2.imencode(".png", make_scene(**options).image)[1].tobytes()


def settings(**changes):
    original = InspectionSettings(
        BOARD, specification=ProductTolerance(DimensionTolerance(65, -1, 1), DimensionTolerance(35, -1, 1)),
        calibration=known_calibration(), product_id="TEST-ONLY", conditions_confirmed=True,
        acquisition_notes="Synthetic fixture for automated software verification only",
    )
    return replace(original, **changes)


def test_calibration_from_images_to_saved_full_flow(tmp_path, monkeypatch):
    # Actually fit a camera from multiple detected boards, load the JSON, and
    # undistort a separate held-out distorted frame. No measurement mocks.
    scan = scan_calibration_images(list(rendered_calibration_images()), CAMERA_BOARD)
    model = calibrate_camera(scan.views, CAMERA_BOARD)
    loaded = calibration_from_json(calibration_to_json(model))
    raw = rendered_product_image()
    payload = cv2.imencode(".png", raw)[1].tobytes()
    captured = []
    real_measure = service.measure_rectangle

    def measure(image, *args, **kwargs):
        captured.append(image.copy())
        return real_measure(image, *args, **kwargs)

    monkeypatch.setattr(service, "measure_rectangle", measure)
    outcome = inspect_image(payload, "held-out-synthetic.png", settings(board=CAMERA_BOARD, calibration=loaded))
    record = outcome.record
    assert record["decision"] == PASS, record["message"]
    assert record["measurement"]["length_mm"] == pytest.approx(65, abs=.8)
    assert record["measurement"]["width_mm"] == pytest.approx(35, abs=.8)
    np.testing.assert_array_equal(captured[0], undistort_image(cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR), loaded))
    assert record["calibration_id"] == loaded.fingerprint
    assert record["calibration"]["distortion"] == loaded.distortion.tolist()
    assert record["stages_completed"] == ["input", "configuration", "calibration", "conditions", "quality", "measurement", "tolerance", "annotation"]
    store = HistoryStore(tmp_path / "lịch sử.sqlite3")
    store.save(outcome)
    reloaded = HistoryStore(store.path).get(record["run_id"])
    assert reloaded == outcome
    assert record["source_sha256"] == sha256(payload).hexdigest()
    assert UUID(record["run_id"]).version == 4
    assert datetime.fromisoformat(record["completed_at"]) >= datetime.fromisoformat(record["started_at"])
    assert record["duration_ms"] > 0


@pytest.mark.parametrize("changes,code", [
    ({"calibration": None}, "MISSING_CALIBRATION"),
    ({"calibration_error": "bad JSON"}, "INVALID_CALIBRATION"),
    ({"calibration": "invalid"}, "INVALID_CALIBRATION"),
    ({"calibration": known_calibration((640, 480))}, "RESOLUTION_MISMATCH"),
    ({"calibration": replace(known_calibration(), rms_px=3., per_view_rmse_px=np.full(5, 3.))}, "INVALID_CALIBRATION"),
    ({"conditions_confirmed": False}, "CONDITIONS_UNCONFIRMED"),
    ({"conditions_confirmed": 1}, "CONDITIONS_UNCONFIRMED"),
    ({"specification": None}, "INVALID_CONFIGURATION"),
    ({"product_id": " "}, "INVALID_CONFIGURATION"),
    ({"near_limit_mm": -1}, "INVALID_CONFIGURATION"),
    ({"near_limit_mm": float("nan")}, "INVALID_CONFIGURATION"),
    ({"segmentation": "unknown"}, "INVALID_CONFIGURATION"),
])
def test_prerequisite_failure_never_calls_measurement(changes, code, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Measurement must not run after a prerequisite failure")
    monkeypatch.setattr(service, "measure_rectangle", forbidden)
    result = inspect_image(image_bytes(), "test.png", settings(**changes))
    assert result.record["error_code"] == code
    assert result.record["decision"] == NOT_EVALUABLE
    assert result.record["measurement"] is None
    assert result.annotated_png is None


@pytest.mark.parametrize("options,code", [
    ({"include_board": False}, "CHESSBOARD_NOT_FOUND"),
    ({"occlude_board": True}, "CHESSBOARD_NOT_FOUND"),
    ({"include_product": False}, "PRODUCT_NOT_FOUND"),
    ({"second_product": True}, "AMBIGUOUS_PRODUCT"),
])
def test_distinct_geometric_failures(options, code):
    outcome = inspect_image(image_bytes(**options), "test.png", settings())
    assert outcome.record["error_code"] == code, outcome.record
    assert outcome.record["error_stage"] == "measurement"
    assert outcome.record["decision"] == NOT_EVALUABLE


@pytest.mark.parametrize("exc,code,state", [
    (UnreliableMappingError("bad mapping"), "UNRELIABLE_MAPPING", "REJECTED"),
    (UnreliableMeasurementError("bad geometry"), "UNRELIABLE_MEASUREMENT", "REJECTED"),
    (RuntimeError("injected fault"), "INTERNAL_ERROR", "ERROR"),
])
def test_unreliable_geometry_and_unexpected_errors_do_not_pass(exc, code, state, monkeypatch):
    def failed(*args, **kwargs):
        raise exc
    monkeypatch.setattr(service, "measure_rectangle", failed)
    outcome = inspect_image(image_bytes(), "test.png", settings())
    assert outcome.record["error_code"] == code
    assert outcome.record["processing_status"] == state
    assert outcome.record["decision"] == NOT_EVALUABLE


def test_mixed_batch_keeps_failures_unique_ids_and_original_order(tmp_path):
    payload = image_bytes()
    outcomes = list(inspect_batch([("same.png", payload), ("bad.png", b"not an image"), ("same.png", payload)], settings()))
    assert [x.record["filename"] for x in outcomes] == ["same.png", "bad.png", "same.png"]
    assert [x.record["decision"] for x in outcomes] == [PASS, NOT_EVALUABLE, PASS]
    assert len({x.record["run_id"] for x in outcomes}) == 3
    assert outcomes[1].record["error_code"] == "INVALID_IMAGE"
    assert outcomes[1].record["product_id"] == "TEST-ONLY"
    assert outcomes[1].record["settings"]["board"] == vars(BOARD)
    store = HistoryStore(tmp_path / "history.sqlite3")
    for outcome in outcomes:
        store.save(outcome)
    assert summarize_records(store.list_records()) == {PASS: 2, FAIL: 0, NOT_EVALUABLE: 1}


def test_dimension_failure_and_near_limit_warning_preserve_measured_values():
    spec = ProductTolerance(DimensionTolerance(64, -0.1, 0.1), DimensionTolerance(35, -1, 1))
    result = inspect_image(image_bytes(), "test.png", settings(specification=spec, near_limit_mm=2.))
    record = result.record
    assert record["processing_status"] == "COMPLETED"
    assert record["decision"] == FAIL
    assert record["dimensions"][0]["status"] == FAIL
    assert record["dimensions"][1]["status"] == PASS
    assert record["dimensions"][0]["near_limit"]
    assert any("Chiều dài gần giới hạn" in w for w in record["warnings"])
    assert record["dimensions"][0]["measured_mm"] == str(record["measurement"]["length_mm"])


@pytest.mark.parametrize("value", [0, 255, 120])
def test_uniform_dark_bright_or_low_contrast_image_is_rejected(value):
    image = np.full((640, 900, 3), value, np.uint8)
    payload = cv2.imencode(".png", image)[1].tobytes()
    outcome = inspect_image(payload, "uniform.png", settings())
    assert outcome.record["error_code"] == "IMAGE_QUALITY"
    assert not outcome.record["quality"]["acceptable"]


def test_blur_screening_and_quality_threshold_validation():
    blurred = cv2.GaussianBlur(make_scene().image, (61, 61), 20)
    result = check_image_quality(blurred, QualityOptions())
    assert not result["acceptable"]
    assert result["laplacian_variance"] < 20


@pytest.mark.parametrize("changes", [{"min_contrast": 256}, {"min_contrast": 0}, {"min_laplacian_variance": float("nan")}, {"min_laplacian_variance": True}])
def test_bad_quality_options(changes):
    with pytest.raises(ValueError):
        QualityOptions(**changes)
