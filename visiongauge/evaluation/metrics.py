"""Error formulas in mm and percent; empty samples never imply zero error."""

import numpy as np


def measurement_errors(reference, measured) -> dict[str, np.ndarray]:
    reference, measured = np.asarray(reference), np.asarray(measured)
    for values in (reference, measured):
        if (values.ndim != 1 or values.dtype.kind not in "fiu"
                or not np.isfinite(values).all() or np.any(values <= 0)):
            raise ValueError("Kích thước phải là vector số hữu hạn, dương.")
    if reference.shape != measured.shape:
        raise ValueError("Số kích thước tham chiếu và kết quả đo phải bằng nhau.")
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        try:
            signed = measured.astype(float) - reference.astype(float)
            absolute = np.abs(signed)
            relative = absolute / reference * 100.0
        except FloatingPointError as exc:
            raise ValueError("Giá trị kích thước vượt miền tính toán.") from exc
    return {"signed_error_mm": signed, "absolute_error_mm": absolute,
            "relative_error_pct": relative}


def error_statistics(reference, measured) -> dict[str, float | int]:
    errors = measurement_errors(reference, measured)
    count = len(errors["signed_error_mm"])
    names = ("mean_error_mm", "mae_mm", "rmse_mm", "max_absolute_error_mm", "mape_pct")
    if not count:
        return {"n": 0, **{name: float("nan") for name in names}}
    signed, absolute = errors["signed_error_mm"], errors["absolute_error_mm"]
    scale = float(absolute.max())
    # Normalize before squaring so large finite errors do not overflow in RMSE.
    rmse = scale * float(np.sqrt(np.mean((signed / scale) ** 2))) if scale else 0.0
    return {"n": count, "mean_error_mm": float(np.mean(signed)),
            "mae_mm": float(np.mean(absolute)), "rmse_mm": rmse,
            "max_absolute_error_mm": scale, "mape_pct": float(np.mean(errors["relative_error_pct"]))}
