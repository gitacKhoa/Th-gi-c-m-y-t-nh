"""Deterministic, supersampled planar scenes with known geometric dimensions.

Generate example inputs with: python -m tests.synthetic --output data/synthetic
These are software fixtures, NOT observations from a physical measuring system.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from visiongauge.calibration import transform_points
from visiongauge.config import ChessboardConfig


BOARD = ChessboardConfig(columns=7, rows=5, square_size_mm=10.0)
LENGTH_MM = 65.0
WIDTH_MM = 35.0


@dataclass(frozen=True)
class SyntheticScene:
    image: np.ndarray
    corners_px: np.ndarray
    product_corners_px: np.ndarray
    world_to_image: np.ndarray


def make_scene(
    angle: float = 0.0, perspective: int = 0, *,
    include_board: bool = True, include_product: bool = True,
    occlude_board: bool = False, bright_product: bool = False,
    noise: bool = False, second_product: bool = False,
    product_center: tuple[float, float] = (150.0, 95.0),
    product_shape: str = "rectangle",
) -> SyntheticScene:
    # A fronto-parallel reference raster uses 4 px/mm; rendering is at 2x scale.
    # Measurement never receives this scale, only the board geometry.
    supersample, pixels_per_mm = 2, 4
    scale = supersample * pixels_per_mm
    background = 35 if bright_product else 230
    image = np.full((640 * supersample, 900 * supersample, 3), background, dtype=np.uint8)

    def fill(points, color):
        cv2.fillConvexPoly(image, np.rint(np.asarray(points) * scale).astype(np.int32), (color,) * 3)

    if include_board:
        fill([[15, 20], [105, 20], [105, 90], [15, 90]], 255)
        for row in range(BOARD.rows + 1):
            for col in range(BOARD.columns + 1):
                x, y = 20 + col * 10, 25 + row * 10
                fill([[x, y], [x + 10, y], [x + 10, y + 10], [x, y + 10]], 15 if (row + col) % 2 == 0 else 255)
        if occlude_board:
            fill([[40, 40], [80, 40], [80, 65], [40, 65]], background)

    product = cv2.boxPoints((product_center, (LENGTH_MM, WIDTH_MM), angle)).astype(np.float64)
    color = 220 if bright_product else 40
    if include_product:
        if product_shape == "rectangle":
            fill(product, color)
        elif product_shape == "circle":
            cv2.circle(image, tuple(np.rint(np.array(product_center) * scale).astype(int)), 20 * scale, (color,) * 3, -1)
        elif product_shape == "trapezoid":
            fill([[125, 80], [190, 80], [177, 115], [138, 115]], color)
    if second_product:
        fill([[140, 132], [170, 132], [170, 145], [140, 145]], color)
    if noise:
        generator = np.random.default_rng(42)
        for x, y in generator.integers([450, 25], [870, 190], size=(25, 2)):
            cv2.circle(image, (int(x * supersample), int(y * supersample)), 2 * supersample, (color,) * 3, -1)

    image = cv2.resize(image, (900, 640), interpolation=cv2.INTER_AREA)
    source = np.float32([[0, 0], [899, 0], [899, 639], [0, 639]])
    destinations = {
        0: source,
        1: np.float32([[45, 40], [850, 12], [875, 600], [15, 615]]),
        2: np.float32([[90, 80], [820, 15], [860, 590], [30, 550]]),
    }
    projective = cv2.getPerspectiveTransform(source, destinations[perspective])
    image = cv2.warpPerspective(image, projective, (900, 640), borderValue=(background,) * 3)
    # World origin is the first inner corner at global coordinates (30, 35) mm.
    # Raster boundaries lie halfway between pixel centres. Resizing the 2x
    # raster preserves this convention: x_mm * 4 - 0.5, not x_mm * 4.
    world_to_image = projective @ np.array([[4, 0, 119.5], [0, 4, 139.5], [0, 0, 1]], dtype=float)
    x, y = np.meshgrid(np.arange(BOARD.columns) * 10.0, np.arange(BOARD.rows) * 10.0)
    corners = transform_points(np.column_stack((x.ravel(), y.ravel())), world_to_image)
    product_px = transform_points(product - [30, 35], world_to_image)
    return SyntheticScene(image, corners, product_px, world_to_image)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic fixtures, not real measurement data.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for angle, perspective in ((0, 0), (23, 1), (57, 2)):
        scene = make_scene(angle, perspective)
        success, encoded = cv2.imencode(".png", scene.image)
        if not success:
            raise RuntimeError("Could not encode synthetic fixture.")
        target = args.output / f"synthetic_65x35mm_angle{angle}_perspective{perspective}.png"
        target.write_bytes(encoded.tobytes())
        print(target)


if __name__ == "__main__":
    main()
