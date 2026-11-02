import numpy as np
import pytest

from visiongauge.calibration import chessboard_points_mm, detect_chessboard, draw_chessboard
from visiongauge.errors import ChessboardNotFoundError
from tests.synthetic import BOARD, make_scene


def test_metric_corner_order():
    points = chessboard_points_mm(BOARD)
    assert points.shape == (35, 2)
    np.testing.assert_array_equal(points[0], [0, 0])
    np.testing.assert_array_equal(points[1], [10, 0])
    np.testing.assert_array_equal(points[7], [0, 10])
    np.testing.assert_array_equal(points[-1], [60, 40])


@pytest.mark.parametrize("method", ["sb", "classic", "auto"])
def test_detect_subpixel_corners_and_draw(method):
    scene = make_scene(perspective=1)
    before = scene.image.copy()
    detection = detect_chessboard(scene.image, BOARD, method=method)
    # A symmetric chessboard may reverse the ordering by 180 degrees.
    error = min(
        np.max(np.linalg.norm(detection.corners_px - expected, axis=1))
        for expected in (scene.corners_px, scene.corners_px[::-1])
    )
    assert error < 0.8
    assert np.any(np.abs(detection.corners_px - np.rint(detection.corners_px)) > 0.01)
    rendered = draw_chessboard(scene.image, detection)
    assert rendered.shape == scene.image.shape
    assert not np.array_equal(rendered, scene.image)
    np.testing.assert_array_equal(before, scene.image)


@pytest.mark.parametrize("scene", [
    {"include_board": False}, {"occlude_board": True},
])
def test_missing_or_occluded_board(scene):
    with pytest.raises(ChessboardNotFoundError):
        detect_chessboard(make_scene(**scene).image, BOARD)


def test_classic_fallback(monkeypatch):
    monkeypatch.setattr("cv2.findChessboardCornersSB", lambda *args, **kwargs: (False, None))
    result = detect_chessboard(make_scene().image, BOARD)
    assert result.method == "classic"


def test_classic_refines_corners(monkeypatch):
    import cv2

    original = cv2.cornerSubPix
    calls = []

    def refine(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(cv2, "cornerSubPix", refine)
    detect_chessboard(make_scene().image, BOARD, method="classic")
    assert calls == [True]
