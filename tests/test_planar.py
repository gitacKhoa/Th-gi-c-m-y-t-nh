import numpy as np
import pytest

from visiongauge.calibration import MappingOptions, chessboard_points_mm, estimate_planar_mapping, transform_points
from visiongauge.errors import UnreliableMappingError
from tests.synthetic import BOARD, make_scene


@pytest.mark.parametrize("perspective", [0, 1, 2])
def test_exact_metric_mapping_and_inverse(perspective):
    scene = make_scene(perspective=perspective)
    mapping = estimate_planar_mapping(scene.corners_px, BOARD)
    points_mm = np.array([[0, 0], [10, 20], [100, 60], [160, 75]], dtype=float)
    pixels = transform_points(points_mm, scene.world_to_image)
    np.testing.assert_allclose(mapping.to_mm(pixels), points_mm, atol=1e-4)
    np.testing.assert_allclose(mapping.to_image(points_mm), pixels, atol=1e-3)
    assert mapping.quality.rmse_px < 1e-4
    assert mapping.board_polygon_px().shape == (4, 2)


@pytest.mark.parametrize("kind", ["missing", "nan", "duplicate", "collinear", "nonlinear", "tiny", "folded"])
def test_reject_unreliable_grid(kind):
    corners = make_scene().corners_px.copy()
    if kind == "missing":
        corners = corners[:-1]
    elif kind == "nan":
        corners[0, 0] = np.nan
    elif kind == "duplicate":
        corners[1] = corners[0]
    elif kind == "collinear":
        corners[:, 1] = corners[:, 0]
    elif kind == "nonlinear":
        corners[:, 0] += 0.003 * (corners[:, 1] - corners[:, 1].mean()) ** 2
    elif kind == "tiny":
        corners *= 0.01
    elif kind == "folded":
        corners[[8, 9]] = corners[[9, 8]]
    with pytest.raises(UnreliableMappingError):
        estimate_planar_mapping(corners, BOARD)


def test_reject_poles_and_bad_matrices():
    pole = np.array([[1, 0, 0], [0, 1, 0], [1, 0, -1]], dtype=float)
    with pytest.raises(UnreliableMappingError):
        transform_points(np.array([[1, 2]]), pole)
    with pytest.raises(UnreliableMappingError):
        transform_points(np.array([[0, 2], [2, 2]]), pole)
    with pytest.raises(UnreliableMappingError):
        transform_points(np.array([[2, 2]]), np.zeros((3, 3)))


def test_reject_excessive_extrapolation():
    mapping = estimate_planar_mapping(make_scene().corners_px, BOARD)
    with pytest.raises(UnreliableMappingError, match="quá xa"):
        mapping.to_mm(mapping.to_image(np.array([[1000, 1000]], dtype=float)))


def test_reject_bad_mapping_options():
    with pytest.raises(ValueError):
        MappingOptions(max_rmse_px=float("nan"))
    with pytest.raises(ValueError):
        MappingOptions(max_rmse_px=2, max_error_px=1)
