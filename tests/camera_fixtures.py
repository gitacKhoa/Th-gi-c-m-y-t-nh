"""Known synthetic pinhole cameras and rendered chessboards; NOT experimental data."""

from functools import lru_cache

import cv2
import numpy as np

from visiongauge.calibration import CalibrationView, CameraCalibration, chessboard_points_mm
from visiongauge.config import ChessboardConfig


CAMERA_BOARD = ChessboardConfig(7, 5, 20.0)
CAMERA_SIZE = (640, 480)
CAMERA_K = np.array([[700., 0, 320], [0, 710., 240], [0, 0, 1]])
CAMERA_D = np.array([-0.12, 0.035, 0.0005, -0.0003, 0.005])
POSES = [
    ((-.35, .15, -.1), (-95, -40, 360)), ((.3, -.3, .08), (-25, -20, 330)),
    ((.15, .35, .18), (-60, -65, 380)), ((-.2, -.35, -.2), (-80, -20, 350)),
    ((.4, .25, .12), (-35, -60, 400)), ((-.3, -.12, .22), (-20, -35, 360)),
    ((.1, -.4, -.16), (-100, -20, 390)), ((.32, .3, .04), (-50, -65, 340)),
    ((-.22, .25, .24), (-75, -50, 370)), ((.18, -.2, -.1), (-30, -40, 400)),
    ((.35, .08, .16), (-60, -10, 360)), ((-.25, -.28, -.02), (-90, -60, 380)),
]


def projected_views(noise=0.0):
    points = np.column_stack((chessboard_points_mm(CAMERA_BOARD), np.zeros(35)))
    rng = np.random.default_rng(23)
    views = []
    for index, (rvec, tvec) in enumerate(POSES):
        projected, _ = cv2.projectPoints(points, np.array(rvec, float), np.array(tvec, float), CAMERA_K, CAMERA_D)
        corners = projected.reshape(-1, 2) + rng.normal(0, noise, (35, 2))
        views.append(CalibrationView(f"synthetic_{index:02d}.png", CAMERA_SIZE, corners))
    return tuple(views)


@lru_cache(maxsize=1)
def rendered_calibration_images():
    """Inverse-render curved grid edges with 2x supersampling from a known camera."""
    width, height = CAMERA_SIZE
    yy, xx = np.indices((height * 2, width * 2), dtype=float)
    raw = np.column_stack((((xx.ravel() + .5) / 2 - .5), ((yy.ravel() + .5) / 2 - .5)))
    rays = cv2.undistortPointsIter(raw.reshape(-1, 1, 2), CAMERA_K, CAMERA_D, None, None, (3, 50, 1e-10)).reshape(-1, 2)
    rays = np.column_stack((rays, np.ones(len(rays))))
    images = []
    for index, (rvec, tvec) in enumerate(POSES):
        rotation, _ = cv2.Rodrigues(np.array(rvec, float))
        plane = np.column_stack((rotation[:, 0], rotation[:, 1], np.array(tvec, float)))
        world = rays @ np.linalg.inv(plane).T
        x, y = (world[:, :2] / world[:, 2, None]).T
        pixels = np.full(len(raw), 225, dtype=np.uint8)
        paper = (x >= -30) & (x < 150) & (y >= -30) & (y < 110)
        board = (x >= -20) & (x < 140) & (y >= -20) & (y < 100)
        cells = (np.floor((x + 20) / 20) + np.floor((y + 20) / 20)).astype(int)
        pixels[paper] = 255
        pixels[board & (cells % 2 == 0)] = 10
        image = cv2.resize(pixels.reshape(height * 2, width * 2), CAMERA_SIZE, interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        images.append((f"synthetic_{index:02d}.png", encoded.tobytes()))
    return tuple(images)


def known_calibration(image_size=(900, 640), distortion=None):
    """Fixture model with declared known parameters, not fitted real observations."""
    width, height = image_size
    matrix = np.array([[width, 0, width / 2], [0, width, height / 2], [0, 0, 1]], dtype=float)
    return CameraCalibration(
        image_size, CAMERA_BOARD, matrix, np.zeros(5) if distortion is None else np.asarray(distortion),
        np.zeros((5, 3)), np.tile([0., 0., 500.], (5, 1)),
        tuple(f"synthetic_reference_{i}" for i in range(5)), np.zeros(5), 0.,
    )


def rendered_product_image():
    """Independent held-out synthetic frame: 65 x 35 mm object beside the board."""
    width, height = CAMERA_SIZE
    yy, xx = np.indices((height * 2, width * 2), dtype=float)
    raw = np.column_stack(((xx.ravel() + .5) / 2 - .5, (yy.ravel() + .5) / 2 - .5))
    rays = cv2.undistortPointsIter(raw.reshape(-1, 1, 2), CAMERA_K, CAMERA_D, None, None, (3, 50, 1e-10)).reshape(-1, 2)
    rotation, _ = cv2.Rodrigues(np.array([.12, -.1, .04]))
    plane = np.column_stack((rotation[:, 0], rotation[:, 1], np.array([-60., -40., 500.])))
    world = np.column_stack((rays, np.ones(len(rays)))) @ np.linalg.inv(plane).T
    x, y = (world[:, :2] / world[:, 2, None]).T
    pixels = np.full(len(raw), 225, dtype=np.uint8)
    pixels[(x >= -30) & (x < 150) & (y >= -30) & (y < 110)] = 255
    board = (x >= -20) & (x < 140) & (y >= -20) & (y < 100)
    cells = (np.floor((x + 20) / 20) + np.floor((y + 20) / 20)).astype(int)
    pixels[board & (cells % 2 == 0)] = 10
    pixels[(x >= 180) & (x <= 245) & (y >= 0) & (y <= 35)] = 40
    return cv2.resize(pixels.reshape(height * 2, width * 2), CAMERA_SIZE, interpolation=cv2.INTER_AREA)
