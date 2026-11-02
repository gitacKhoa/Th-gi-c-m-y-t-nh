"""Strict UTF-8 manifest with user-provided caliper references and conditions."""

import csv
from pathlib import Path, PurePosixPath, PureWindowsPath

import numpy as np
import pandas as pd

from visiongauge.errors import VisionGaugeError


REQUIRED_COLUMNS = ("image_path", "product_id", "reference_length_mm", "reference_width_mm", "condition_id")
OPTIONAL_COLUMNS = ("camera_id", "lighting", "view_angle_deg", "camera_distance_mm",
                    "reference_instrument", "captured_at", "notes")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def normalize_image_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or PureWindowsPath(value).drive
            or ".." in path.parts or ":" in value or path.suffix.lower() not in IMAGE_SUFFIXES):
        raise VisionGaugeError("image_path phải là đường dẫn ảnh tương đối bên trong thư mục ảnh.")
    return path.as_posix()


def read_manifest(path: str | Path) -> pd.DataFrame:
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if len(header) != len(set(header)) or not set(REQUIRED_COLUMNS).issubset(header):
                raise ValueError(f"Cần các cột không trùng: {', '.join(REQUIRED_COLUMNS)}.")
            if set(header) - set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS):
                raise ValueError("CSV có tên cột không được hỗ trợ; kiểm tra lại tiêu đề mẫu.")
            records = []
            for values in reader:
                if not values or all(not value.strip() for value in values):
                    continue
                if len(values) != len(header):
                    raise ValueError(f"Dòng {reader.line_num}: số ô không khớp tiêu đề.")
                row = dict(zip(header, (value.strip() for value in values)))
                if any(not row[key] for key in REQUIRED_COLUMNS):
                    raise ValueError(f"Dòng {reader.line_num}: thiếu trường bắt buộc.")
                row["image_path"] = normalize_image_path(row["image_path"])
                for key in ("reference_length_mm", "reference_width_mm"):
                    row[key] = float(row[key])
                    if not np.isfinite(row[key]) or row[key] <= 0:
                        raise ValueError(f"Dòng {reader.line_num}: {key} phải hữu hạn và > 0.")
                if row["reference_length_mm"] < row["reference_width_mm"]:
                    raise ValueError(f"Dòng {reader.line_num}: chiều dài phải >= chiều rộng.")
                for key in OPTIONAL_COLUMNS:
                    row.setdefault(key, "")
                for key, low, high in (("view_angle_deg", 0, 90), ("camera_distance_mm", 0, np.inf)):
                    if row[key] != "":
                        row[key] = float(row[key])
                        if (not np.isfinite(row[key]) or not low <= row[key] <= high
                                or (key == "camera_distance_mm" and row[key] == 0)):
                            raise ValueError(f"Dòng {reader.line_num}: {key} không hợp lệ.")
                records.append(row)
        if not records:
            raise ValueError("CSV chưa có dữ liệu. Hãy điền kích thước thực đo bằng thước cặp.")
        table = pd.DataFrame(records, columns=REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
        if table.image_path.str.casefold().duplicated().any():
            raise ValueError("image_path bị trùng (không phân biệt hoa/thường trên Windows).")
        return table
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        raise VisionGaugeError(f"Dataset không hợp lệ: {exc}") from exc


def resolve_image_path(root: Path, relative: str) -> Path:
    path = (root / normalize_image_path(relative)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise VisionGaugeError("Đường dẫn ảnh hoặc liên kết trỏ ra ngoài thư mục dataset.")
    return path
