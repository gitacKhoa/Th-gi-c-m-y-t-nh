"""Batch measurement using the existing pipeline, with full per-image failure records."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import platform

import cv2
import numpy as np
import pandas as pd

from visiongauge import __version__
from visiongauge.calibration import CameraCalibration, undistort_image
from visiongauge.config import ChessboardConfig
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image
from visiongauge.measurement import measure_rectangle
from visiongauge.processing import ContourOptions
from .dataset import IMAGE_SUFFIXES, REQUIRED_COLUMNS, OPTIONAL_COLUMNS, read_manifest, resolve_image_path
from .metrics import measurement_errors
from .summary import summarize_results


@dataclass
class EvaluationReport:
    results: pd.DataFrame
    metadata: dict

    @property
    def summaries(self) -> dict[str, pd.DataFrame]:
        return {
            "overall": summarize_results(self.results),
            "by_product": summarize_results(self.results, ("product_id",)),
            "by_condition": summarize_results(self.results, ("condition_id",)),
            "by_product_condition": summarize_results(self.results, ("product_id", "condition_id")),
        }


def evaluate_dataset(
    images_dir: str | Path, manifest_path: str | Path, board: ChessboardConfig, *,
    calibration: CameraCalibration | None = None, image_geometry: str | None = None,
    segmentation: str = "threshold",
) -> EvaluationReport:
    if not isinstance(board, ChessboardConfig):
        raise VisionGaugeError("Cần cấu hình bàn cờ hợp lệ.")
    if calibration is not None:
        if image_geometry is not None:
            raise VisionGaugeError("Chọn calibration hoặc điều kiện ảnh, không đồng thời cả hai.")
        if calibration.rms_px > 1.0 or max(calibration.per_view_rmse_px) > 2.0:
            raise VisionGaugeError("Calibration vượt ngưỡng RMS 1 px / RMSE từng ảnh 2 px.")
        geometry = "undistorted"
    else:
        if image_geometry not in ("undistorted", "negligible_distortion"):
            raise VisionGaugeError("Cần calibration hoặc xác nhận điều kiện méo ảnh.")
        geometry = image_geometry
    options = ContourOptions(method=segmentation)
    root, manifest = Path(images_dir).resolve(), Path(manifest_path).resolve()
    if not root.is_dir():
        raise VisionGaugeError("Không tìm thấy thư mục ảnh dataset.")
    table = read_manifest(manifest)
    records = table.to_dict("records")
    declared = set(table.image_path.str.casefold())
    # Include unlabelled images as failures, instead of silently omitting them.
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            relative = path.relative_to(root).as_posix()
            if relative.casefold() not in declared:
                records.append({**{key: "" for key in REQUIRED_COLUMNS + OPTIONAL_COLUMNS},
                                "image_path": relative, "reference_length_mm": np.nan, "reference_width_mm": np.nan})
    rows = []
    for record in records:
        row = {**record, "status": "failed", "error_type": "", "error_message": "", "image_sha256": "",
               "image_width_px": np.nan, "image_height_px": np.nan, "board_rmse_px": np.nan,
               "warnings": "", "calibration_id": calibration.fingerprint if calibration else "",
               "image_geometry": "calibrated" if calibration else geometry, "segmentation": segmentation}
        for dimension in ("length", "width"):
            row[f"measured_{dimension}_mm"] = np.nan
            for kind in ("signed_error_mm", "absolute_error_mm", "relative_error_pct"):
                row[f"{dimension}_{kind}"] = np.nan
        if not record["product_id"]:
            row.update(status="missing_metadata", error_type="MissingMetadata",
                       error_message="Ảnh có trong thư mục nhưng chưa được khai báo trong CSV.")
            rows.append(row)
            continue
        try:
            path = resolve_image_path(root, record["image_path"])
            payload = path.read_bytes()
            row["image_sha256"] = sha256(payload).hexdigest()
            image = decode_image(payload)
            row["image_height_px"], row["image_width_px"] = image.shape[:2]
            if calibration:
                image = undistort_image(image, calibration)
            result = measure_rectangle(image, board, image_geometry=geometry, contour_options=options)
            # Validate both dimensions before committing a successful row.
            errors = measurement_errors(
                [record["reference_length_mm"], record["reference_width_mm"]],
                [result.length_mm, result.width_mm],
            )
            for index, (dimension, value) in enumerate((("length", result.length_mm), ("width", result.width_mm))):
                row[f"measured_{dimension}_mm"] = value
                for kind, values in errors.items():
                    row[f"{dimension}_{kind}"] = float(values[index])
            row.update(status="success", board_rmse_px=result.mapping.quality.rmse_px,
                       warnings=" | ".join(result.warnings))
        except (VisionGaugeError, OSError, cv2.error, ValueError) as exc:
            row.update(error_type=type(exc).__name__, error_message=str(exc))
        rows.append(row)
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "visiongauge_version": __version__,
        "python_version": platform.python_version(), "opencv_version": cv2.__version__,
        "numpy_version": np.__version__, "pandas_version": pd.__version__,
        "images_dir": str(root), "manifest_path": str(manifest),
        "manifest_sha256": sha256(manifest.read_bytes()).hexdigest(), "board": vars(board),
        "calibration_id": calibration.fingerprint if calibration else None,
        "image_geometry": "calibrated" if calibration else geometry, "contour_options": vars(options),
        "aggregation": "One successful image is one sample; failures excluded from error metrics but counted.",
    }
    return EvaluationReport(pd.DataFrame(rows), metadata)
