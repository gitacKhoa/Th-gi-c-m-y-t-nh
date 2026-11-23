"""Temporary synthetic datasets exercise batch, exports, figures and Windows CLI."""

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
import pandas as pd
import pytest

from tests.camera_fixtures import known_calibration
from tests.synthetic import make_scene
from tests.test_evaluation_dataset import HEADER
from tests.test_evaluation_metrics import summary_fixture
from visiongauge.calibration import save_calibration
from visiongauge.config import ChessboardConfig, PROJECT_ROOT
from visiongauge.errors import VisionGaugeError
from visiongauge.evaluation import evaluate_dataset
from visiongauge.evaluation.__main__ import main
from visiongauge.evaluation.plots import comparison_figure
from visiongauge.evaluation.reporting import export_report


BOARD = ChessboardConfig(7, 5, 10.)


def write_scene(path: Path, **options):
    path.parent.mkdir(parents=True, exist_ok=True)
    success, image = cv2.imencode(".png", make_scene(**options).image)
    assert success
    path.write_bytes(image.tobytes())


def dataset(tmp_path):
    images = tmp_path / "ảnh tổng hợp"
    write_scene(images / "nhóm/ảnh.png", angle=23, perspective=1)
    manifest = tmp_path / "tham chiếu tổng hợp.csv"
    manifest.write_text(HEADER + "\nnhóm/ảnh.png,001,65,35,synthetic\n", encoding="utf-8-sig")
    return images, manifest


def test_real_pipeline_keeps_failures_and_unlisted_images(tmp_path):
    images, manifest = dataset(tmp_path)
    write_scene(images / "second.png", angle=57, perspective=2)
    write_scene(images / "no_board.png", include_board=False)
    write_scene(images / "no_product.png", include_product=False)
    write_scene(images / "unlisted.png")
    (images / "broken.png").write_bytes(b"invalid")
    with manifest.open("a", encoding="utf-8") as stream:
        stream.write("second.png,001,65,35,rotated\nno_board.png,002,65,35,synthetic\n"
                     "no_product.png,003,65,35,synthetic\nbroken.png,004,65,35,synthetic\n"
                     "missing.png,005,65,35,synthetic\n")
    report = evaluate_dataset(images, manifest, BOARD, image_geometry="undistorted")
    result = report.results.set_index("image_path")
    assert len(result) == 7 and (result.status == "success").sum() == 2
    assert result.loc["nhóm/ảnh.png", "measured_length_mm"] == pytest.approx(65, abs=.8)
    assert result.loc["nhóm/ảnh.png", "measured_width_mm"] == pytest.approx(35, abs=.8)
    row = result.loc["second.png"]
    assert row.length_absolute_error_mm == pytest.approx(abs(row.measured_length_mm - 65))
    assert row.width_relative_error_pct == pytest.approx(abs(row.measured_width_mm - 35) / 35 * 100)
    assert result.loc["unlisted.png", "status"] == "missing_metadata"
    assert result.loc["missing.png", "error_type"] == "FileNotFoundError"
    failed = result[result.status != "success"]
    assert failed.measured_length_mm.isna().all() and failed.length_absolute_error_mm.isna().all()
    assert failed.error_message.str.len().gt(0).all()
    assert report.summaries["overall"].success_rate_pct.iloc[0] == pytest.approx(200 / 7)


def test_calibrated_batch_and_resolution_failure(tmp_path):
    images, manifest = dataset(tmp_path)
    model = known_calibration()
    report = evaluate_dataset(images, manifest, BOARD, calibration=model, segmentation="canny")
    assert report.results.status.tolist() == ["success"]
    assert report.results.calibration_id.iloc[0] == model.fingerprint
    assert report.metadata["image_geometry"] == "calibrated"
    assert report.metadata["contour_options"]["method"] == "canny"
    mismatch = evaluate_dataset(images, manifest, BOARD, calibration=known_calibration((640, 480)))
    assert mismatch.results.status.iloc[0] == "failed"
    assert "độ phân giải" in mismatch.results.error_message.iloc[0]
    assert mismatch.summaries["overall"].mae_mm.isna().all()


def test_batch_requires_explicit_geometry_and_valid_fit(tmp_path):
    images, manifest = dataset(tmp_path)
    with pytest.raises(VisionGaugeError):
        evaluate_dataset(images, manifest, BOARD)
    with pytest.raises(VisionGaugeError):
        evaluate_dataset(images, manifest, BOARD, calibration=known_calibration(), image_geometry="undistorted")
    bad = replace(known_calibration(), rms_px=3., per_view_rmse_px=np.full(5, 3.))
    with pytest.raises(VisionGaugeError):
        evaluate_dataset(images, manifest, BOARD, calibration=bad)
    with pytest.raises(VisionGaugeError):
        evaluate_dataset(images / "absent", manifest, BOARD, image_geometry="undistorted")


def test_csv_export_plot_metadata_and_overwrite_protection(tmp_path):
    images, manifest = dataset(tmp_path)
    report = evaluate_dataset(images, manifest, BOARD, image_geometry="undistorted")
    output = export_report(report, tmp_path / "báo cáo")
    assert {path.name for path in output.iterdir()} == {
        "results.csv", "failed_images.csv", "overall.csv", "by_product.csv", "by_condition.csv",
        "by_product_condition.csv", "reference_vs_measured.png", "run_metadata.json",
    }
    results = pd.read_csv(output / "results.csv", dtype={"product_id": str})
    assert results.product_id.iloc[0] == "001" and results.image_path.iloc[0] == "nhóm/ảnh.png"
    assert pd.read_csv(output / "failed_images.csv").empty
    overall = pd.read_csv(output / "overall.csv")
    assert overall.mae_mm.iloc[0] == pytest.approx(abs(results.measured_length_mm.iloc[0] - 65), abs=1e-7)
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["board"]["square_size_mm"] == 10 and len(metadata["manifest_sha256"]) == 64
    image = cv2.imdecode(np.frombuffer((output / "reference_vs_measured.png").read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image.shape[:2] == (720, 1600) and image.std() > 5
    with pytest.raises(VisionGaugeError, match="ghi đè"):
        export_report(report, output)
    with pytest.raises(VisionGaugeError, match="ngoài"):
        export_report(report, images / "report")


def test_plot_shows_correct_points_and_excludes_failed_rows():
    figure = comparison_figure(summary_fixture())
    try:
        assert len(figure.axes) == 2
        np.testing.assert_array_equal(figure.axes[0].collections[0].get_offsets(), [[100, 103], [100, 99], [200, 204]])
        np.testing.assert_array_equal(figure.axes[1].collections[0].get_offsets(), [[50, 49], [50, 52], [100, 100]])
        assert "3/5" in figure._suptitle.get_text()
        np.testing.assert_array_equal(figure.axes[0].lines[0].get_xdata(), figure.axes[0].lines[0].get_ydata())
    finally:
        figure.clear()


def test_all_failed_report_preserves_missing_metrics(tmp_path):
    images, manifest = dataset(tmp_path)
    (images / "nhóm/ảnh.png").write_bytes(b"broken")
    report = evaluate_dataset(images, manifest, BOARD, image_geometry="undistorted")
    output = export_report(report, tmp_path / "failed_run")
    overall = pd.read_csv(output / "overall.csv")
    assert overall.n.tolist() == [0, 0]
    assert overall.mae_mm.isna().all() and overall.rmse_mm.isna().all()
    assert overall.success_rate_pct.eq(0).all()
    assert len(pd.read_csv(output / "failed_images.csv")) == 1
    figure = comparison_figure(report.results)
    assert not figure.axes[0].collections
    assert figure.axes[0].texts[0].get_text() == "No successful measurements"
    figure.clear()


def cli_args(images, manifest, output):
    return ["--images", str(images), "--metadata", str(manifest), "--columns", "7", "--rows", "5",
            "--square-size-mm", "10", "--image-geometry", "undistorted", "--output", str(output)]


def test_cli_end_to_end_with_unicode_paths(tmp_path):
    images, manifest = dataset(tmp_path)
    output = tmp_path / "kết quả"
    process = subprocess.run([sys.executable, "-m", "visiongauge.evaluation", *cli_args(images, manifest, output)],
                             cwd=PROJECT_ROOT, capture_output=True, encoding="utf-8", timeout=60,
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert process.returncode == 0, process.stderr
    assert "successful: 1" in process.stdout and (output / "results.csv").is_file()


def test_cli_failure_exit_codes_and_calibration_option(tmp_path, capsys):
    images, manifest = dataset(tmp_path)
    model_path = tmp_path / "camera.json"
    save_calibration(model_path, known_calibration())
    args = cli_args(images, manifest, tmp_path / "calibrated_run")
    index = args.index("--image-geometry")
    args[index:index + 2] = ["--calibration", str(model_path)]
    assert main(args) == 0
    (images / "nhóm/ảnh.png").write_bytes(b"broken")
    assert main(cli_args(images, manifest, tmp_path / "partial_run")) == 1
    assert "failed/missing metadata: 1" in capsys.readouterr().out
    manifest.write_text(HEADER + "\n", encoding="utf-8")
    output = tmp_path / "invalid_run"
    assert main(cli_args(images, manifest, output)) == 2
    assert not output.exists()
    assert "chưa có dữ liệu" in capsys.readouterr().err
