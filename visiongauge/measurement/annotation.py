"""Render diagnostic corners and dimensions on a copy of the input image."""

import cv2
import numpy as np

from visiongauge.calibration import ChessboardDetection, draw_chessboard


def annotate_measurement(
    image: np.ndarray, board: ChessboardDetection, corners_px: np.ndarray,
    length_mm: float, width_mm: float, corners_mm: np.ndarray,
) -> np.ndarray:
    annotated = draw_chessboard(image, board)
    polygon = np.rint(corners_px).astype(np.int32)
    cv2.polylines(annotated, [polygon], True, (0, 180, 0), 2, cv2.LINE_AA)
    lengths = np.linalg.norm(np.roll(corners_mm, -1, axis=0) - corners_mm, axis=1)
    longest = int(np.argmax(lengths))
    for edge, label in ((longest, f"L: {length_mm:.2f} mm"), ((longest + 1) % 4, f"W: {width_mm:.2f} mm")):
        start, end = polygon[edge], polygon[(edge + 1) % 4]
        cv2.arrowedLine(annotated, tuple(start), tuple(end), (0, 100, 230), 2, cv2.LINE_AA, tipLength=0.05)
        cv2.arrowedLine(annotated, tuple(end), tuple(start), (0, 100, 230), 2, cv2.LINE_AA, tipLength=0.05)
        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        midpoint = (start + end) // 2
        x = max(0, min(int(midpoint[0]), annotated.shape[1] - text_size[0] - 2))
        y = max(text_size[1] + 2, min(int(midpoint[1]) - 8, annotated.shape[0] - 4))
        cv2.putText(annotated, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(annotated, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 60, 180), 1, cv2.LINE_AA)
    return annotated
