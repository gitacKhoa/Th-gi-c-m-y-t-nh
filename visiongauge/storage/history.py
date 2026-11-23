"""SQLite history with atomic image + metadata writes and idempotent retries."""

from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

from visiongauge.config import PROJECT_ROOT
from visiongauge.workflow.models import RunOutcome, PASS, FAIL, NOT_EVALUABLE


class HistoryError(RuntimeError):
    """Persistence failed; the caller must retain unsaved runs for retry."""


def default_history_path() -> Path:
    """Override for deployments/tests; never derived from an uploaded filename."""
    return Path(os.environ.get("VISIONGAUGE_HISTORY_DB", str(PROJECT_ROOT / "data" / "history.sqlite3")))


class HistoryStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_history_path()

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise HistoryError(f"Phiên bản lịch sử {version} chưa được hỗ trợ.")
            connection.execute("""CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, product_id TEXT NOT NULL,
                decision TEXT NOT NULL, record_json TEXT NOT NULL,
                source_bytes BLOB NOT NULL, annotated_png BLOB
            )""")
            connection.execute("CREATE INDEX IF NOT EXISTS runs_time ON runs(started_at)")
            connection.execute("PRAGMA user_version=1")
            connection.commit()
            return connection
        except Exception:
            connection.close()
            raise

    def save(self, outcome: RunOutcome) -> bool:
        """True if inserted, False for an identical retry. Never overwrite a run."""
        record = outcome.record
        try:
            UUID(record["run_id"])
            datetime.fromisoformat(record["started_at"])
            if record["decision"] not in (PASS, FAIL, NOT_EVALUABLE):
                raise ValueError("Trạng thái đánh giá không hợp lệ.")
            if record["processing_status"] not in ("COMPLETED", "REJECTED", "ERROR"):
                raise ValueError("Chỉ lưu lượt đo đã kết thúc.")
            if record["processing_status"] != "COMPLETED" and record["decision"] != NOT_EVALUABLE:
                raise ValueError("Lượt đo thất bại không được phân loại đạt/không đạt.")
            payload = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT record_json, source_bytes, annotated_png FROM runs WHERE run_id=?", (record["run_id"],)
                ).fetchone()
                if existing is not None:
                    if tuple(existing) != (payload, outcome.source_bytes, outcome.annotated_png):
                        raise HistoryError("Mã lượt đo đã tồn tại với nội dung khác; không ghi đè lịch sử.")
                    return False
                connection.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    record["run_id"], record["started_at"], record["product_id"], record["decision"],
                    payload, outcome.source_bytes, outcome.annotated_png,
                ))
            return True
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as exc:
            raise HistoryError(f"Không lưu được lịch sử: {exc}") from exc

    def list_records(self) -> list[dict]:
        """Metadata only: reading the history table does not load image blobs."""
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute("SELECT record_json FROM runs ORDER BY started_at DESC, rowid DESC")
                return [json.loads(row[0]) for row in rows]
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise HistoryError(f"Không đọc được lịch sử: {exc}") from exc

    def get(self, run_id: str) -> RunOutcome:
        try:
            with closing(self._connect()) as connection:
                row = connection.execute("SELECT record_json, source_bytes, annotated_png FROM runs WHERE run_id=?", (run_id,)).fetchone()
                if row is None:
                    raise HistoryError("Không tìm thấy mã lượt đo trong lịch sử.")
                return RunOutcome(json.loads(row[0]), row[1], row[2])
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise HistoryError(f"Không đọc được chi tiết lượt đo: {exc}") from exc


def summarize_records(records: list[dict]) -> dict[str, int]:
    counts = {PASS: 0, FAIL: 0, NOT_EVALUABLE: 0}
    for record in records:
        counts[record["decision"]] += 1
    return counts
