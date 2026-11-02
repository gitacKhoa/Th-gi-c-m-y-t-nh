"""Calibration-page state, invalidated whenever the dataset or board changes."""

from dataclasses import dataclass
from hashlib import sha256
import json

from visiongauge.calibration import (
    CalibrationScan, CameraCalibration, calibrate_camera, scan_calibration_images,
)
from visiongauge.config import ChessboardConfig
from visiongauge.errors import VisionGaugeError


@dataclass
class CalibrationWorkflow:
    fingerprint: str | None = None
    scan: CalibrationScan | None = None
    result: CameraCalibration | None = None
    error: str | None = None

    def update(self, images: list[tuple[str, bytes]], board: ChessboardConfig) -> None:
        identity = [vars(board), [(name, sha256(data).hexdigest()) for name, data in images]]
        fingerprint = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        if fingerprint != self.fingerprint:
            self.fingerprint = fingerprint
            self.scan = None
            self.result = None
            self.error = None

    def detect(self, images: list[tuple[str, bytes]], board: ChessboardConfig) -> None:
        self.scan, self.result, self.error = None, None, None
        try:
            self.scan = scan_calibration_images(images, board)
        except VisionGaugeError as exc:
            self.error = str(exc)

    def calibrate(self, images: list[tuple[str, bytes]], board: ChessboardConfig) -> None:
        self.result, self.error = None, None
        if self.scan is None:
            self.detect(images, board)
        if self.scan is not None:
            try:
                self.result = calibrate_camera(self.scan.views, board)
            except VisionGaugeError as exc:
                self.error = str(exc)
