"""UTF-8 CSV export of actual saved runs, retaining failures and exact decimals."""

import csv
from io import StringIO
import json


BASE_FIELDS = ["run_id", "started_at", "completed_at", "duration_ms", "product_id", "filename", "source",
               "processing_status", "decision", "error_stage", "error_code", "message", "calibration_id",
               "source_sha256", "rule_id", "warnings", "settings_json", "calibration_json", "quality_json"]
DIMENSION_FIELDS = ["nominal_mm", "lower_limit_mm", "upper_limit_mm", "measured_mm", "deviation_mm",
                    "status", "near_limit", "distance_to_limit_mm"]
CSV_FIELDS = BASE_FIELDS + [f"{name}_{field}" for name in ("length", "width") for field in DIMENSION_FIELDS]


def safe_csv_text(value):
    """Prevent uploaded filenames/notes from becoming spreadsheet formulas."""
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


def records_to_csv(records: list[dict]) -> bytes:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for record in records:
        row = {field: safe_csv_text(record.get(field)) for field in BASE_FIELDS}
        row["warnings"] = safe_csv_text(" | ".join(record["warnings"]))
        for key in ("settings", "calibration", "quality"):
            row[f"{key}_json"] = json.dumps(record.get(key), ensure_ascii=False, allow_nan=False)
        for dimension in record["dimensions"]:
            for field in DIMENSION_FIELDS:
                row[f"{dimension['name']}_{field}"] = dimension[field]
        writer.writerow(row)
    return stream.getvalue().encode("utf-8-sig")
