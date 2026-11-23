"""Manifest integrity, Windows paths, and user-filled blank template."""

import pytest

from visiongauge.config import PROJECT_ROOT
from visiongauge.errors import VisionGaugeError
from visiongauge.evaluation.dataset import read_manifest, resolve_image_path


HEADER = "image_path,product_id,reference_length_mm,reference_width_mm,condition_id"


def test_utf8_manifest_keeps_identifiers_and_normalizes_windows_paths(tmp_path):
    csv = tmp_path / "đo.csv"
    csv.write_text(HEADER + ',lighting,view_angle_deg,camera_distance_mm,notes\n'
                   'nhóm\\ảnh.jpg,0001,160.2,80.1,001,"đèn trái, tán sáng",15,500,\n', encoding="utf-8-sig")
    row = read_manifest(csv).iloc[0]
    assert row.product_id == "0001" and row.condition_id == "001"
    assert row.image_path == "nhóm/ảnh.jpg" and row.reference_length_mm == 160.2
    assert row.lighting == "đèn trái, tán sáng" and row.view_angle_deg == 15
    assert row.reference_instrument == ""


@pytest.mark.parametrize("body", [
    "", HEADER + "\n", "filename,length,width\na.jpg,160,80\n",
    HEADER + ",product_id\na.jpg,A,160,80,C,A\n",
    HEADER + ",unknown\na.jpg,A,160,80,C,x\n",
    HEADER + "\na.jpg,A,160,80\n",
    HEADER + "\na.jpg,,160,80,C\n",
    HEADER + "\na.jpg,A,0,80,C\n",
    HEADER + "\na.jpg,A,160,-1,C\n",
    HEADER + "\na.jpg,A,nan,80,C\n",
    HEADER + "\na.jpg,A,160,inf,C\n",
    HEADER + "\na.jpg,A,80,160,C\n",
    HEADER + "\na.jpg,A,160,80,C\nA.JPG,A,160,80,C\n",
    HEADER + "\n../outside.jpg,A,160,80,C\n",
    HEADER + "\nC:/outside.jpg,A,160,80,C\n",
    HEADER + "\n//server/share/a.jpg,A,160,80,C\n",
    HEADER + "\na.txt,A,160,80,C\n",
    HEADER + ",view_angle_deg\na.jpg,A,160,80,C,91\n",
    HEADER + ",camera_distance_mm\na.jpg,A,160,80,C,0\n",
    HEADER + ",camera_distance_mm\na.jpg,A,160,80,C,nan\n",
])
def test_invalid_manifest_is_rejected_before_measurement(tmp_path, body):
    path = tmp_path / "measurements.csv"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(VisionGaugeError, match="Dataset"):
        read_manifest(path)


def test_template_has_no_invented_experimental_rows():
    path = PROJECT_ROOT / "datasets/template/measurements.csv"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    with pytest.raises(VisionGaugeError, match="chưa có dữ liệu"):
        read_manifest(path)


def test_missing_manifest_and_path_traversal(tmp_path):
    with pytest.raises(VisionGaugeError):
        read_manifest(tmp_path / "missing.csv")
    with pytest.raises(VisionGaugeError):
        resolve_image_path(tmp_path, "../outside.jpg")
    assert resolve_image_path(tmp_path, "nested/a.jpg") == tmp_path / "nested/a.jpg"
