"""python -m visiongauge.evaluation --help"""

import argparse
from pathlib import Path
import sys

from visiongauge.calibration import load_calibration
from visiongauge.config import ChessboardConfig
from .batch import evaluate_dataset
from .reporting import export_report, validate_output_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đánh giá phép đo bằng ảnh và kích thước thước cặp thực tế.")
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh, gồm các thư mục con")
    parser.add_argument("--metadata", type=Path, required=True, help="CSV tham chiếu và điều kiện chụp")
    parser.add_argument("--columns", type=int, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--square-size-mm", type=float, required=True)
    geometry = parser.add_mutually_exclusive_group(required=True)
    geometry.add_argument("--calibration", type=Path, help="JSON calibration cho ảnh thô")
    geometry.add_argument("--image-geometry", choices=("undistorted", "negligible_distortion"))
    parser.add_argument("--segmentation", choices=("threshold", "canny"), default="threshold")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục báo cáo mới, ngoài thư mục ảnh")
    args = parser.parse_args(argv)
    try:
        validate_output_directory(args.output, args.images)
        board = ChessboardConfig(args.columns, args.rows, args.square_size_mm)
        model = load_calibration(args.calibration) if args.calibration else None
        report = evaluate_dataset(args.images, args.metadata, board, calibration=model,
                                  image_geometry=args.image_geometry, segmentation=args.segmentation)
        output = export_report(report, args.output)
    except (ValueError, OSError) as exc:
        print(f"KHÔNG THỂ ĐÁNH GIÁ: {exc}", file=sys.stderr)
        return 2
    successful = int((report.results.status == "success").sum())
    failed = len(report.results) - successful
    print(f"Images: {len(report.results)}; successful: {successful}; failed/missing metadata: {failed}")
    print(report.summaries["overall"].to_string(index=False, na_rep="N/A"))
    print(f"Report: {output}")
    print("Error metrics use successful images only. No accuracy certification or tolerance decision is implied.")
    return 1 if failed else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
