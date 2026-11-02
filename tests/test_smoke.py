"""Dependency and module smoke tests; these do not evaluate measurement accuracy."""

import importlib
import sqlite3

import cv2
import pytest


@pytest.mark.parametrize("module", [
    "numpy", "pandas", "matplotlib", "streamlit",
    "visiongauge.image_io", "visiongauge.calibration", "visiongauge.processing",
    "visiongauge.measurement", "visiongauge.tolerance", "visiongauge.ui",
    "visiongauge.storage",
])
def test_module_imports(module):
    importlib.import_module(module)


def test_required_chessboard_apis_available():
    for name in ("findChessboardCornersSB", "findChessboardCorners",
                 "cornerSubPix", "calibrateCamera", "undistort"):
        assert callable(getattr(cv2, name))


def test_sqlite_available():
    with sqlite3.connect(":memory:") as connection:
        assert connection.execute("SELECT 1").fetchone() == (1,)
