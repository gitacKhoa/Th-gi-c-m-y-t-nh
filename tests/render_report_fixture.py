"""Render a labelled SOFTWARE-TEST report for visual QA, never production history.

Run: python -m tests.render_report_fixture --output tmp/pdfs
"""

import argparse
from pathlib import Path

import pypdfium2 as pdfium

from tests.test_full_flow import image_bytes, settings
from visiongauge.reporting import records_to_pdf
from visiongauge.tolerance import DimensionTolerance, ProductTolerance
from visiongauge.workflow import inspect_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    note = "DỮ LIỆU TỔNG HỢP CHỈ KIỂM THỬ PHẦN MỀM - KHÔNG PHẢI KẾT QUẢ THỰC NGHIỆM."
    passed = inspect_image(image_bytes(angle=23, perspective=1), "ảnh tổng hợp.png",
                           settings(product_id="TEST ONLY - ĐẠT", acquisition_notes=note))
    failed = inspect_image(image_bytes(), "ảnh tổng hợp ngoài dung sai.png", settings(
        product_id="TEST ONLY - KHÔNG ĐẠT", acquisition_notes=note,
        specification=ProductTolerance(DimensionTolerance(64, -.1, .1), DimensionTolerance(35, -1, 1)),
        near_limit_mm=2.,
    ))
    unknown = inspect_image(b"not an image", "ảnh lỗi kiểm thử.png", settings(product_id="TEST ONLY - LỖI", acquisition_notes=note))
    outcomes = [passed, failed, unknown]
    report = records_to_pdf([outcome.record for outcome in outcomes], annotated_images={
        outcome.record["run_id"]: outcome.annotated_png for outcome in outcomes if outcome.annotated_png
    })
    (args.output / "software_test_report.pdf").write_bytes(report)
    with pdfium.PdfDocument(report) as document:
        for index, page in enumerate(document):
            bitmap = page.render(scale=1.4)
            image = bitmap.to_pil()
            image.save(args.output / f"software_test_page_{index + 1}.png")
            image.close()
            bitmap.close()
            page.close()
        print(f"Rendered {len(document)} pages for visual review: {args.output}")


if __name__ == "__main__":
    main()
