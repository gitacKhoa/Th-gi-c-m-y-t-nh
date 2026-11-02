"""Chessboard detection, multi-view camera calibration and planar mapping."""

from .camera import CalibrationScan, CalibrationView, calibrate_camera, scan_calibration_images
from .camera_model import (
    CameraCalibration, calibration_from_json, calibration_to_json, load_calibration,
    save_calibration, undistort_image, undistort_image_points,
)

from .chessboard import ChessboardDetection, chessboard_points_mm, detect_chessboard, draw_chessboard
from .planar import MappingOptions, MappingQuality, PlanarMapping, estimate_planar_mapping, transform_points

__all__ = [
    "CalibrationScan", "CalibrationView", "calibrate_camera", "scan_calibration_images",
    "CameraCalibration", "calibration_from_json", "calibration_to_json", "load_calibration",
    "save_calibration", "undistort_image", "undistort_image_points",
    "ChessboardDetection", "chessboard_points_mm", "detect_chessboard", "draw_chessboard",
    "MappingOptions", "MappingQuality", "PlanarMapping", "estimate_planar_mapping", "transform_points",
]
