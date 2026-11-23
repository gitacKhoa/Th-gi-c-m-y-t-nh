"""Calibrate -> screen -> measure -> inspect. No UI, storage, or synthetic fallback."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
from time import perf_counter
from uuid import uuid4

import cv2

from visiongauge import __version__
from visiongauge.calibration import CameraCalibration, calibration_to_json, undistort_image
from visiongauge.config import ChessboardConfig
from visiongauge.errors import (
    AmbiguousProductError, CameraCalibrationError, ChessboardNotFoundError,
    InvalidImageError, ProductNotFoundError, UnreliableMappingError,
    UnreliableMeasurementError, VisionGaugeError,
)
from visiongauge.image_io import decode_image
from visiongauge.measurement import measure_rectangle
from visiongauge.processing import ContourOptions
from visiongauge.tolerance import ProductTolerance, evaluate_tolerance, InspectionStatus
from visiongauge.tolerance.models import as_decimal
from .models import InspectionSettings, RunOutcome, NOT_EVALUABLE
from .quality import QualityOptions, check_image_quality


class _Rejected(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def specification_snapshot(specification: ProductTolerance) -> dict:
    return {name: {key: str(value) for key, value in vars(getattr(specification, name)).items()}
            for name in ("length", "width")}


def inspect_image(data: bytes, filename: str, settings: InspectionSettings, *, source="file") -> RunOutcome:
    """One explicit attempt, including failures. Calibration is always required.

    Failed prerequisites never call measurement. No resize/crop or uncalibrated
    fallback is allowed. Synthetic images exist only in tests, not in this API.
    """
    started = perf_counter()
    record = {
        "schema_version": 1, "run_id": str(uuid4()), "started_at": _utc_now(),
        "completed_at": None, "duration_ms": None, "app_version": __version__,
        "filename": str(filename), "source": str(source), "product_id": "",
        "source_sha256": sha256(data).hexdigest() if isinstance(data, bytes) else None,
        "processing_status": "RUNNING", "decision": NOT_EVALUABLE,
        "error_code": None, "error_stage": None, "message": "",
        "stages_completed": [], "settings": {}, "calibration_id": None,
        "calibration": None, "quality": None, "measurement": None,
        "dimensions": [], "warnings": [], "rule_id": None,
    }
    stage = "input"
    png = None
    # Preserve valid supplied context even when decoding fails. This is a
    # snapshot of the request, never evidence that its prerequisites passed.
    if isinstance(settings, InspectionSettings):
        record["product_id"] = settings.product_id if isinstance(settings.product_id, str) else ""
        if (isinstance(settings.board, ChessboardConfig) and isinstance(settings.specification, ProductTolerance)
                and isinstance(settings.quality, QualityOptions)):
            record["settings"] = {
                "board": asdict(settings.board), "specification": specification_snapshot(settings.specification),
                "segmentation": str(settings.segmentation), "quality": asdict(settings.quality),
                "near_limit_mm": str(settings.near_limit_mm), "conditions_confirmed": settings.conditions_confirmed is True,
                "acquisition_notes": str(settings.acquisition_notes),
            }
        if isinstance(settings.calibration, CameraCalibration):
            record["calibration_id"] = settings.calibration.fingerprint
            record["calibration"] = json.loads(calibration_to_json(settings.calibration))
    try:
        if not isinstance(data, bytes) or len(data) > 20_000_000:
            raise InvalidImageError("Cần dữ liệu ảnh bytes, tối đa 20 MB.")
        image = decode_image(data)
        record["image_size"] = list(image.shape[1::-1])
        record["stages_completed"].append(stage)
        stage = "configuration"
        if not isinstance(settings, InspectionSettings):
            raise _Rejected("INVALID_CONFIGURATION", "Cấu hình lượt đo không hợp lệ.")
        record["product_id"] = settings.product_id if isinstance(settings.product_id, str) else ""
        if (not isinstance(settings.board, ChessboardConfig)
                or not isinstance(settings.specification, ProductTolerance)
                or not isinstance(settings.quality, QualityOptions)
                or settings.segmentation not in ("threshold", "canny")
                or not isinstance(settings.acquisition_notes, str)):
            raise _Rejected("INVALID_CONFIGURATION", "Cần cấu hình bàn cờ, tiêu chuẩn và dung sai hợp lệ.")
        if not record["product_id"].strip() or len(record["product_id"]) > 120:
            raise _Rejected("INVALID_CONFIGURATION", "Mã sản phẩm cần từ 1 đến 120 ký tự.")
        try:
            near = as_decimal(settings.near_limit_mm, "Ngưỡng cảnh báo gần giới hạn")
            if near < 0:
                raise ValueError("Ngưỡng cảnh báo phải >= 0 mm.")
        except ValueError as exc:
            raise _Rejected("INVALID_CONFIGURATION", str(exc)) from exc
        record["settings"] = {
            "board": asdict(settings.board), "specification": specification_snapshot(settings.specification),
            "segmentation": settings.segmentation, "quality": asdict(settings.quality),
            "near_limit_mm": str(near), "conditions_confirmed": settings.conditions_confirmed is True,
            "acquisition_notes": settings.acquisition_notes,
        }
        record["stages_completed"].append(stage)
        stage = "calibration"
        calibration = settings.calibration
        if settings.calibration_error:
            raise _Rejected("INVALID_CALIBRATION", str(settings.calibration_error))
        if calibration is None:
            raise _Rejected("MISSING_CALIBRATION", "Chưa có calibration. Nạp hoặc tạo calibration trước khi đo.")
        if not isinstance(calibration, CameraCalibration):
            raise _Rejected("INVALID_CALIBRATION", "Thông số calibration không hợp lệ.")
        record["calibration_id"] = calibration.fingerprint
        record["calibration"] = json.loads(calibration_to_json(calibration))
        if calibration.rms_px > 1.0 or max(calibration.per_view_rmse_px) > 2.0:
            raise _Rejected("INVALID_CALIBRATION", "Calibration vượt RMS tổng 1 px hoặc RMS từng ảnh 2 px.")
        if image.shape[1::-1] != calibration.image_size:
            raise _Rejected("RESOLUTION_MISMATCH", f"Ảnh {image.shape[1::-1]} khác calibration {calibration.image_size}; không tự resize/crop.")
        image = undistort_image(image, calibration)
        record["stages_completed"].append(stage)
        stage = "conditions"
        if settings.conditions_confirmed is not True:
            raise _Rejected("CONDITIONS_UNCONFIRMED", "Cần xác nhận cùng camera/zoom/focus, bàn cờ và sản phẩm đồng phẳng, mẫu đúng kích thước.")
        record["stages_completed"].append(stage)
        stage = "quality"
        record["quality"] = check_image_quality(image, settings.quality)
        if not record["quality"]["acceptable"]:
            raise _Rejected("IMAGE_QUALITY", " ".join(record["quality"]["reasons"]))
        record["stages_completed"].append(stage)
        stage = "measurement"
        result = measure_rectangle(image, settings.board, image_geometry="undistorted",
                                   contour_options=ContourOptions(method=settings.segmentation))
        record["measurement"] = {
            "length_mm": result.length_mm, "width_mm": result.width_mm,
            "corners_mm": result.rectangle.corners_mm.tolist(), "corners_px": result.corners_px.tolist(),
            "homography_image_to_mm": result.mapping.image_to_mm.tolist(),
            "mapping_quality": asdict(result.mapping.quality),
        }
        record["warnings"].extend(result.warnings)
        quality = result.mapping.quality
        if quality.rmse_px >= 0.8 * result.mapping.options.max_rmse_px:
            record["warnings"].append("Sai số khớp homography gần ngưỡng loại; nên chụp lại để kiểm tra.")
        if record["quality"]["laplacian_variance"] < 2 * settings.quality.min_laplacian_variance:
            record["warnings"].append("Độ nét gần ngưỡng loại; kiểm tra focus trước khi dùng kết luận.")
        record["stages_completed"].append(stage)
        stage = "tolerance"
        inspection = evaluate_tolerance(result.length_mm, result.width_mm, settings.specification,
                                        measurement_succeeded=True)
        if inspection.status == InspectionStatus.NOT_EVALUABLE:
            raise UnreliableMeasurementError(inspection.reason)
        record["rule_id"] = inspection.rule_id
        for dimension in inspection.dimensions:
            spec = dimension.specification
            margin = min(abs(dimension.measured_mm - spec.lower_limit_mm),
                         abs(dimension.measured_mm - spec.upper_limit_mm))
            close = margin <= near
            record["dimensions"].append({
                "name": dimension.name, "nominal_mm": str(spec.nominal_mm),
                "lower_limit_mm": str(spec.lower_limit_mm), "upper_limit_mm": str(spec.upper_limit_mm),
                "measured_mm": str(dimension.measured_mm), "deviation_mm": str(dimension.deviation_mm),
                "status": dimension.status.value, "reason": dimension.reason,
                "near_limit": close, "distance_to_limit_mm": str(margin),
            })
            if close:
                label = "Chiều dài" if dimension.name == "length" else "Chiều rộng"
                record["warnings"].append(f"{label} gần giới hạn dung sai: cách {margin} mm (ngưỡng {near} mm).")
        record["stages_completed"].append(stage)
        stage = "annotation"
        ok, encoded = cv2.imencode(".png", result.annotated_image)
        if not ok:
            raise VisionGaugeError("Không tạo được ảnh chú thích.")
        png = encoded.tobytes()
        record["stages_completed"].append(stage)
        record.update(processing_status="COMPLETED", decision=inspection.status.value, message=inspection.reason)
    except _Rejected as exc:
        record.update(processing_status="REJECTED", error_code=exc.code, error_stage=stage, message=str(exc))
    except (VisionGaugeError, cv2.error) as exc:
        codes = {InvalidImageError: "INVALID_IMAGE", CameraCalibrationError: "INVALID_CALIBRATION",
                 ChessboardNotFoundError: "CHESSBOARD_NOT_FOUND", ProductNotFoundError: "PRODUCT_NOT_FOUND",
                 AmbiguousProductError: "AMBIGUOUS_PRODUCT", UnreliableMappingError: "UNRELIABLE_MAPPING",
                 UnreliableMeasurementError: "UNRELIABLE_MEASUREMENT"}
        record.update(processing_status="REJECTED", error_code=codes.get(type(exc), "PROCESSING_ERROR"),
                      error_stage=stage, message=str(exc))
    except Exception:
        logging.getLogger(__name__).exception("Unexpected inspection failure %s at %s", record["run_id"], stage)
        record.update(processing_status="ERROR", error_code="INTERNAL_ERROR", error_stage=stage,
                      message="Lỗi xử lý nội bộ. Tra log bằng mã lượt đo; không dùng kết quả này.")
    if record["processing_status"] != "COMPLETED":
        record["decision"] = NOT_EVALUABLE
        record["measurement"] = None
        record["dimensions"] = []
        png = None
    record["completed_at"] = _utc_now()
    record["duration_ms"] = round((perf_counter() - started) * 1000, 3)
    return RunOutcome(record, data if isinstance(data, bytes) else b"", png)


def inspect_batch(images, settings: InspectionSettings, *, source="file"):
    """Yield attempts in input order; one rejected image does not stop the next."""
    for filename, data in images:
        yield inspect_image(data, filename, settings, source=source)
