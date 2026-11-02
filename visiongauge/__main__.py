"""Run one file measurement without Streamlit: python -m visiongauge --help."""

import argparse
from pathlib import Path
import sys

import cv2

from visiongauge.config import ChessboardConfig, ConfigurationError
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import read_image
from visiongauge.measurement import measure_rectangle
from visiongauge.processing import ContourOptions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VisionGauge: đo một sản phẩm chữ nhật với bàn cờ.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--columns", type=int, required=True, help="Số góc trong theo chiều ngang")
    parser.add_argument("--rows", type=int, required=True, help="Số góc trong theo chiều dọc")
    parser.add_argument("--square-size-mm", type=float, required=True)
    parser.add_argument("--image-geometry", choices=("undistorted", "negligible_distortion"), required=True)
    parser.add_argument("--segmentation", choices=("threshold", "canny"), default="threshold")
    parser.add_argument("--output", type=Path, help="Lưu ảnh chú thích định dạng PNG")
    args = parser.parse_args(argv)
    try:
        config = ChessboardConfig(args.columns, args.rows, args.square_size_mm)
        result = measure_rectangle(
            read_image(args.image), config, image_geometry=args.image_geometry,
            contour_options=ContourOptions(method=args.segmentation),
        )
        if args.output:
            if args.output.suffix.lower() != ".png":
                raise ValueError("Ảnh đầu ra phải có phần mở rộng .png.")
            if args.output.resolve() == args.image.resolve():
                raise ValueError("Ảnh đầu ra phải khác ảnh đầu vào.")
            success, encoded = cv2.imencode(".png", result.annotated_image)
            if not success:
                raise ValueError("Không mã hóa được ảnh kết quả.")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(encoded.tobytes())
    except (VisionGaugeError, ConfigurationError, OSError, ValueError) as exc:
        print(f"KHÔNG THỂ ĐÁNH GIÁ: {exc}", file=sys.stderr)
        return 2
    print(f"Length: {result.length_mm:.3f} mm; width: {result.width_mm:.3f} mm")
    print(f"Board reprojection RMSE: {result.mapping.quality.rmse_px:.3f} px")
    for warning in result.warnings:
        print(warning)
    return 0


if __name__ == "__main__":
    # Windows redirected terminals may default to cp1252, which cannot encode
    # Vietnamese error messages. Keep the CLI's text contract explicitly UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
