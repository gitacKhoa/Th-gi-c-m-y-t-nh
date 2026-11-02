"""CSV, provenance JSON and plot exports into a fresh report directory."""

import json
from pathlib import Path

from visiongauge.errors import VisionGaugeError
from .batch import EvaluationReport
from .plots import comparison_figure


def validate_output_directory(output_dir: str | Path, images_dir: str | Path) -> Path:
    output, images = Path(output_dir).resolve(), Path(images_dir).resolve()
    if output.is_relative_to(images):
        raise VisionGaugeError("Thư mục báo cáo phải nằm ngoài thư mục ảnh đầu vào.")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise VisionGaugeError("Thư mục báo cáo đã có dữ liệu. Hãy chọn thư mục mới để tránh ghi đè.")
    return output


def export_report(report: EvaluationReport, output_dir: str | Path) -> Path:
    output = validate_output_directory(output_dir, report.metadata["images_dir"])
    summaries = report.summaries
    output.mkdir(parents=True, exist_ok=True)
    tables = {"results": report.results, "failed_images": report.results[report.results.status != "success"], **summaries}
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False, encoding="utf-8-sig", na_rep="", float_format="%.10g")
    figure = comparison_figure(report.results)
    try:
        figure.savefig(output / "reference_vs_measured.png", dpi=160)
    finally:
        figure.clear()
    (output / "run_metadata.json").write_text(
        json.dumps(report.metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8",
    )
    return output
