import cv2
import numpy as np
import pytest

from tests.camera_fixtures import known_calibration
from tests.synthetic import BOARD, make_scene
from visiongauge.errors import VisionGaugeError
from visiongauge.measurement.comparison import compare_measurements, read_references_csv, summarize_comparison


def input_images():
    _, encoded = cv2.imencode(".png", make_scene(23, 1).image)
    return [("synthetic.png", encoded.tobytes()), ("broken.png", b"broken")]


def test_no_references_no_accuracy_claim_and_failures_retained():
    table = compare_measurements(input_images(), BOARD, known_calibration())
    assert len(table) == 2
    assert summarize_comparison(table).empty
    assert table.loc[1, "raw_error"] and table.loc[1, "corrected_error"]
    assert np.isnan(table.loc[1, "corrected_length_mm"])


def test_paired_summary_uses_same_successful_images():
    table = compare_measurements(input_images(), BOARD, known_calibration(), {"synthetic.png": (65, 35), "broken.png": (65, 35)})
    summary = summarize_comparison(table)
    assert len(summary) == 2
    assert (summary.paired_images == 1).all()
    assert (summary.excluded_images == 1).all()
    assert summary.iloc[0].length_mae_mm == pytest.approx(summary.iloc[1].length_mae_mm, abs=1e-4)
    assert table.loc[0, "raw_length_mm"] == pytest.approx(65, abs=.8)


@pytest.mark.parametrize("data", [
    b"file,length,width\na,65,35\n", b"filename,length_mm,width_mm\na,-1,2\n",
    b"filename,length_mm,width_mm\na,1,2\n", b"filename,length_mm,width_mm\na,65,35\na,65,35\n",
    b"filename,length_mm,width_mm\na,nan,35\n", b"",
])
def test_references_invalid(data):
    with pytest.raises(VisionGaugeError):
        read_references_csv(data)


def test_reference_filename_matching():
    refs = read_references_csv(b"filename,length_mm,width_mm\nunknown.png,65,35\n")
    with pytest.raises(VisionGaugeError, match="tên file"):
        compare_measurements(input_images(), BOARD, known_calibration(), refs)
