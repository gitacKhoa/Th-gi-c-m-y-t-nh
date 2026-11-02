"""Image-weighted summaries with explicit success/failure denominators."""

import pandas as pd

from .metrics import error_statistics


def summarize_results(table: pd.DataFrame, group_by: tuple[str, ...] = ()) -> pd.DataFrame:
    required = {"status", *group_by, *(
        f"{prefix}_{dimension}_mm" for prefix in ("reference", "measured") for dimension in ("length", "width")
    )}
    if not required.issubset(table.columns):
        raise ValueError("Bảng kết quả thiếu cột cần để tổng hợp.")
    groups = table.groupby(list(group_by), dropna=False, sort=True) if group_by else [((), table)]
    rows = []
    for key, group in groups:
        key = key if isinstance(key, tuple) else (key,)
        successful = group[group.status == "success"]
        total, success = len(group), len(successful)
        for dimension in ("length", "width"):
            stats = error_statistics(
                successful[f"reference_{dimension}_mm"].to_numpy(dtype=float),
                successful[f"measured_{dimension}_mm"].to_numpy(dtype=float),
            )
            rows.append({**dict(zip(group_by, key)), "dimension": dimension,
                         "total_images": total, "success_images": success, "failed_images": total - success,
                         "success_rate_pct": 100.0 * success / total if total else float("nan"), **stats})
    columns = [*group_by, "dimension", "total_images", "success_images", "failed_images", "success_rate_pct",
               "n", "mean_error_mm", "mae_mm", "rmse_mm", "max_absolute_error_mm", "mape_pct"]
    return pd.DataFrame(rows, columns=columns)
