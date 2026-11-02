"""Per-session UI workflow; delegates all measurement to the existing pipeline."""

from dataclasses import dataclass
from hashlib import sha256
import json

import cv2
import numpy as np

from visiongauge.calibration import CameraCalibration, ChessboardDetection, detect_chessboard, draw_chessboard, undistort_image
from visiongauge.config import ChessboardConfig
from visiongauge.errors import ChessboardNotFoundError, VisionGaugeError
from visiongauge.image_io import decode_image
from visiongauge.measurement import MeasurementResult, measure_rectangle
from visiongauge.processing import ContourOptions


@dataclass
class MeasurementWorkflow:
    fingerprint: str | None = None
    image: np.ndarray | None = None
    raw_image: np.ndarray | None = None
    calibration_id: str | None = None
    board_config: ChessboardConfig | None = None
    image_geometry: str | None = None
    segmentation: str = "threshold"
    detection: ChessboardDetection | None = None
    board_preview: np.ndarray | None = None
    result: MeasurementResult | None = None
    result_png: bytes | None = None
    input_error: str | None = None
    board_error: str | None = None
    measurement_error: str | None = None

    def clear(self) -> None:
        """Drop every cached artifact, including download bytes."""
        self.__dict__.update(MeasurementWorkflow().__dict__)

    def update_input(
        self, data: bytes | None, board: ChessboardConfig, *,
        source: str, image_geometry: str | None, segmentation: str,
        calibration: CameraCalibration | None = None,
    ) -> None:
        context = json.dumps(
            [board.columns, board.rows, board.square_size_mm, source, image_geometry, segmentation,
             calibration.fingerprint if calibration is not None else None],
            ensure_ascii=True,
        ).encode("utf-8")
        payload = b"N" if data is None else b"B" + data
        fingerprint = sha256(context + b"\0" + payload).hexdigest()
        if fingerprint == self.fingerprint:
            return
        self.clear()
        self.fingerprint = fingerprint
        self.board_config = board
        self.image_geometry = image_geometry
        self.segmentation = segmentation
        if data is not None:
            try:
                self.raw_image = decode_image(data)
                if image_geometry == "calibrated":
                    if calibration is None:
                        raise VisionGaugeError("Chưa có calibration đang áp dụng. Hãy nạp hoặc tạo tại trang Camera Calibration.")
                    self.image = undistort_image(self.raw_image, calibration)
                    self.image_geometry = "undistorted"
                    self.calibration_id = calibration.fingerprint
                else:
                    self.image = self.raw_image.copy()
            except VisionGaugeError as exc:
                self.input_error = str(exc)

    def detect(self) -> None:
        self.detection = None
        self.board_preview = None
        self.result = None
        self.result_png = None
        self.board_error = None
        self.measurement_error = None
        if self.image is None or self.board_config is None:
            self.board_error = "Hãy cung cấp ảnh hợp lệ và cấu hình bàn cờ trước."
            return
        try:
            self.detection = detect_chessboard(self.image, self.board_config)
            self.board_preview = draw_chessboard(self.image, self.detection)
        except (VisionGaugeError, cv2.error) as exc:
            self.detection = None
            self.board_error = str(exc) if isinstance(exc, VisionGaugeError) else "OpenCV không xử lý được ảnh bàn cờ này."

    def measure(self) -> None:
        self.result = None
        self.result_png = None
        self.measurement_error = None
        if self.image is None or self.board_config is None:
            self.measurement_error = "Hãy cung cấp ảnh hợp lệ và cấu hình bàn cờ trước."
            return
        if self.image_geometry not in ("undistorted", "negligible_distortion"):
            self.measurement_error = "Cần xác nhận ảnh đã khử méo hoặc méo không đáng kể trước khi đo."
            return
        if self.detection is None:
            self.detect()
            if self.detection is None:
                return
        try:
            result = measure_rectangle(
                self.image, self.board_config, image_geometry=self.image_geometry,
                contour_options=ContourOptions(method=self.segmentation),
            )
            ok, encoded = cv2.imencode(".png", result.annotated_image)
            if not ok:
                raise VisionGaugeError("Không tạo được ảnh PNG kết quả. Hãy thử đo lại.")
            preview = draw_chessboard(self.image, result.board)
            self.result = result
            self.result_png = encoded.tobytes()
            self.detection = result.board
            self.board_preview = preview
            self.board_error = None
        except ChessboardNotFoundError as exc:
            self.detection = None
            self.board_preview = None
            self.board_error = str(exc)
        except (VisionGaugeError, cv2.error) as exc:
            self.measurement_error = str(exc) if isinstance(exc, VisionGaugeError) else "OpenCV không xử lý được ảnh sản phẩm này."
