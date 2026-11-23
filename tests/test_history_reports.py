"""Persistence/report tests use isolated temporary databases and labelled fixtures."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import csv
from io import BytesIO, StringIO
import json
import sqlite3

from pypdf import PdfReader
import pypdfium2 as pdfium
import pytest

from tests.test_full_flow import image_bytes, settings
from visiongauge.reporting import records_to_csv, records_to_pdf
from visiongauge.storage import HistoryError, HistoryStore, summarize_records
from visiongauge.workflow import RunOutcome, inspect_image
from visiongauge.workflow.models import PASS, FAIL, NOT_EVALUABLE


@pytest.fixture(scope="module")
def outcome():
    return inspect_image(image_bytes(), "ảnh kiểm thử.png", settings(product_id="TEST ONLY - Không phải đo thực nghiệm"))


def test_save_reopen_retry_immutable_and_images_atomic(tmp_path, outcome):
    store = HistoryStore(tmp_path / "dữ liệu" / "history.sqlite3")
    assert store.save(outcome)
    assert not store.save(outcome)
    assert len(store.list_records()) == 1
    assert HistoryStore(store.path).get(outcome.record["run_id"]) == outcome
    edited = deepcopy(outcome.record)
    edited["product_id"] = "changed"
    with pytest.raises(HistoryError, match="không ghi đè"):
        store.save(RunOutcome(edited, outcome.source_bytes, outcome.annotated_png))
    assert store.get(outcome.record["run_id"]) == outcome


def test_concurrent_retry_produces_one_row(tmp_path, outcome):
    store = HistoryStore(tmp_path / "history.sqlite3")
    store.list_records()  # Initialize the schema before concurrent requests.
    with ThreadPoolExecutor(max_workers=4) as executor:
        saved = list(executor.map(lambda _: store.save(outcome), range(4)))
    assert saved.count(True) == 1
    assert len(store.list_records()) == 1


def test_transaction_rollback_does_not_leave_orphan_record(tmp_path, outcome):
    store = HistoryStore(tmp_path / "history.sqlite3")
    store.list_records()
    with sqlite3.connect(store.path) as conn:
        conn.execute("CREATE TRIGGER fail_save BEFORE INSERT ON runs BEGIN SELECT RAISE(ABORT, 'simulated disk/write failure'); END")
    with pytest.raises(HistoryError):
        store.save(outcome)
    assert store.list_records() == []


def test_read_write_failures_are_explicit(tmp_path, outcome):
    blocker = tmp_path / "file-not-directory"
    blocker.write_text("blocked")
    store = HistoryStore(blocker / "history.sqlite3")
    with pytest.raises(HistoryError):
        store.save(outcome)
    with pytest.raises(HistoryError):
        store.list_records()
    with pytest.raises(HistoryError):
        HistoryStore(tmp_path / "empty.sqlite3").get("' OR 1=1 --")


def test_future_database_version_is_not_silently_overwritten(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=42")
    with pytest.raises(HistoryError, match="chưa được hỗ trợ"):
        HistoryStore(path).list_records()


def test_csv_keeps_failures_exact_numbers_unicode_and_sanitizes_formulas(outcome):
    failed = inspect_image(b"bad", "=1+1.png", settings(product_id="@TEST"))
    records = [outcome.record, failed.record]
    rows = list(csv.DictReader(StringIO(records_to_csv(records).decode("utf-8-sig"))))
    assert len(rows) == 2
    assert rows[0]["length_measured_mm"] == outcome.record["dimensions"][0]["measured_mm"]
    assert rows[0]["filename"] == "ảnh kiểm thử.png"
    assert rows[1]["filename"] == "'=1+1.png"
    assert rows[1]["product_id"] == "'@TEST"
    assert rows[1]["decision"] == NOT_EVALUABLE
    assert rows[1]["length_measured_mm"] == ""
    assert rows[1]["error_code"] == "INVALID_IMAGE"
    assert json.loads(rows[0]["calibration_json"]) == outcome.record["calibration"]


def test_empty_reports_have_headers_and_zero_counts():
    assert summarize_records([]) == {PASS: 0, FAIL: 0, NOT_EVALUABLE: 0}
    assert list(csv.DictReader(StringIO(records_to_csv([]).decode("utf-8-sig")))) == []
    pdf = PdfReader(BytesIO(records_to_pdf([])))
    assert len(pdf.pages) == 1
    assert "Số lượt đo trong báo cáo: 0" in pdf.pages[0].extract_text()


def test_pdf_roundtrip_vietnamese_status_measurements_and_actual_annotation(outcome):
    failed = inspect_image(b"bad", "invalid.png", settings())
    report = records_to_pdf([outcome.record, failed.record], annotated_images={outcome.record["run_id"]: outcome.annotated_png})
    reader = PdfReader(BytesIO(report))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for expected in (outcome.record["run_id"], failed.record["run_id"], "ĐẠT", "KHÔNG THỂ ĐÁNH GIÁ", "INVALID_IMAGE", "Chi tiết lượt đo", "Không phải đo thực nghiệm"):
        assert expected in text
    assert any(page.images for page in reader.pages)
    # Render every page to exercise font/image decoding independently of text extraction.
    with pdfium.PdfDocument(report) as document:
        for page in document:
            bitmap = page.render(scale=1)
            image = bitmap.to_pil()
            assert image.width > 500 and image.height > 800
            image.close()
            bitmap.close()
            page.close()


def test_long_names_and_xml_characters_are_wrapped_safely(outcome):
    record = deepcopy(outcome.record)
    record["filename"] = "<ảnh & kiểm thử>" * 20
    record["settings"]["acquisition_notes"] = "Ghi chú & điều kiện <đo> " * 80
    reader = PdfReader(BytesIO(records_to_pdf([record])))
    assert len(reader.pages) >= 2
    assert "<ảnh & kiểm thử>" in "".join(p.extract_text() for p in reader.pages)
