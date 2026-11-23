"""Configurable image screening; these scores do not estimate accuracy in mm."""

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

from visiongauge.image_io.images import to_gray


@dataclass(frozen=True)
class QualityOptions:
    min_laplacian_variance: float = 20.0
    min_contrast: float = 20.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} phải hữu hạn và > 0.")
        if self.min_contrast > 255:
            raise ValueError("Ngưỡng tương phản không được vượt 255.")


def check_image_quality(image: np.ndarray, options: QualityOptions) -> dict:
    gray = to_gray(image)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    low, high = np.percentile(gray, [5, 95])
    contrast = float(high - low)
    reasons = []
    if sharpness < options.min_laplacian_variance:
        reasons.append("Ảnh thiếu nét theo ngưỡng Laplacian; kiểm tra focus và rung camera.")
    if contrast < options.min_contrast:
        reasons.append("Độ tương phản thấp; kiểm tra ánh sáng và nền.")
    return {"laplacian_variance": sharpness, "contrast_p95_p05": contrast,
            "mean_intensity": float(gray.mean()), "acceptable": not reasons, "reasons": reasons}
