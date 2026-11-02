"""Paired before/after evaluation; no accuracy claims without reference measurements."""

from io import BytesIO

import numpy as np
import pandas as pd

from visiongauge.calibration import CameraCalibration, undistort_image
from visiongauge.config import ChessboardConfig
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image
from .pipeline import measure_rectangle


def read_references_csv(data: bytes) -> dict[str, tuple[float, float]]:
    try:
        table = pd.read_csv(BytesIO(data), encoding="utf-8-sig")
        if set(table.columns) != {"filename", "length_mm", "width_mm"} or table.empty:
            raise ValueError("Cần ba cột filename,length_mm,width_mm và ít nhất một dòng.")
        if table["filename"].isna().any() or table["filename"].duplicated().any():
            raise ValueError("Tên ảnh tham chiếu bị thiếu hoặc trùng.")
        numbers = table[["length_mm", "width_mm"]].to_numpy(dtype=float)
        if not np.isfinite(numbers).all() or np.any(numbers <= 0) or np.any(numbers[:, 0] < numbers[:, 1]):
            raise ValueError("Kích thước tham chiếu phải hữu hạn, dương, chiều dài >= chiều rộng.")
        return {str(row.filename): (float(row.length_mm), float(row.width_mm)) for row in table.itertuples()}
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise VisionGaugeError(f"CSV tham chiếu không hợp lệ: {exc}") from exc


def compare_measurements(
    images: list[tuple[str, bytes]], board: ChessboardConfig, calibration: CameraCalibration,
    references: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Raw branch deliberately ignores distortion as a BASELINE, not a valid assertion.

    The same input bytes, chessboard geometry and default segmentation are used
    in both branches. Failed images stay in the report with missing dimensions.
    """
    if not images or len({name for name, _ in images}) != len(images):
        raise VisionGaugeError("Cần ảnh sản phẩm và các tên file không trùng nhau.")
    references = references or {}
    if set(references) - {name for name, _ in images}:
        raise VisionGaugeError("CSV có tên file không nằm trong bộ ảnh so sánh.")
    for values in references.values():
        if len(values) != 2 or not np.isfinite(values).all() or min(values) <= 0 or values[0] < values[1]:
            raise VisionGaugeError("Kích thước tham chiếu không hợp lệ.")
    rows = []
    for name, data in images:
        row = {"filename": name, "calibration_id": calibration.fingerprint,
               "reference_length_mm": references.get(name, (np.nan, np.nan))[0],
               "reference_width_mm": references.get(name, (np.nan, np.nan))[1]}
        for branch in ("raw", "corrected"):
            row.update({f"{branch}_length_mm": np.nan, f"{branch}_width_mm": np.nan, f"{branch}_error": ""})
            try:
                image = decode_image(data)
                if branch == "corrected":
                    image = undistort_image(image, calibration)
                result = measure_rectangle(
                    image, board, image_geometry="undistorted" if branch == "corrected" else "negligible_distortion",
                )
                row[f"{branch}_length_mm"] = result.length_mm
                row[f"{branch}_width_mm"] = result.width_mm
            except VisionGaugeError as exc:
                row[f"{branch}_error"] = str(exc)
            for dimension in ("length", "width"):
                row[f"{branch}_{dimension}_error_mm"] = row[f"{branch}_{dimension}_mm"] - row[f"reference_{dimension}_mm"]
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_comparison(table: pd.DataFrame) -> pd.DataFrame:
    """MAE/RMSE on the SAME successful, referenced pairs only; empty without truth."""
    required = [f"{prefix}_{dimension}_mm" for prefix in ("reference", "raw", "corrected") for dimension in ("length", "width")]
    paired = table.dropna(subset=required)
    if paired.empty:
        return pd.DataFrame()
    rows = []
    for branch in ("raw", "corrected"):
        row = {"branch": branch, "paired_images": len(paired), "excluded_images": len(table) - len(paired)}
        for dimension in ("length", "width"):
            errors = paired[f"{branch}_{dimension}_mm"] - paired[f"reference_{dimension}_mm"]
            row[f"{dimension}_mae_mm"] = float(np.mean(np.abs(errors)))
            row[f"{dimension}_rmse_mm"] = float(np.sqrt(np.mean(errors ** 2)))
        rows.append(row)
    return pd.DataFrame(rows)
