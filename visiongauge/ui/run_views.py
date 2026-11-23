"""Shared current-run and historical-run presentation, always from snapshots."""

import pandas as pd
import streamlit as st

from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image
from visiongauge.storage import summarize_records
from visiongauge.workflow.models import RunOutcome, PASS, FAIL


def render_counts(records: list[dict]) -> None:
    columns = st.columns(3)
    for column, (name, count) in zip(columns, summarize_records(records).items()):
        column.metric(name, count)


def records_table(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Mã lượt đo": r["run_id"], "Thời gian UTC": r["started_at"], "Sản phẩm": r["product_id"],
        "Ảnh": r["filename"], "Kết luận": r["decision"], "Trạng thái xử lý": r["processing_status"],
        "Mã lỗi": r["error_code"] or "", "Thời gian (ms)": r["duration_ms"],
    } for r in records])


def render_run_detail(outcome: RunOutcome, *, key: str) -> None:
    record = outcome.record
    st.subheader(f"Lượt đo {record['run_id'][:8]}")
    st.caption(f"Mã đầy đủ: {record['run_id']} · {record['started_at']} UTC · {record['duration_ms']} ms")
    alert = st.success if record["decision"] == PASS else st.error if record["decision"] == FAIL else st.warning
    alert(f"{record['decision']}: {record['message']}")
    if record["error_code"]:
        st.error(f"{record['error_code']} · bước {record['error_stage']} · {record['processing_status']}")
    dimensions = record["dimensions"]
    if dimensions:
        cols = st.columns(2)
        for col, d in zip(cols, dimensions):
            label = "Chiều dài" if d["name"] == "length" else "Chiều rộng"
            col.metric(f"{label} (mm)", f"{float(d['measured_mm']):.3f}")
        st.dataframe(pd.DataFrame([{
            "Kích thước": "Chiều dài" if d["name"] == "length" else "Chiều rộng",
            "Danh nghĩa (mm)": d["nominal_mm"], "Dưới (mm)": d["lower_limit_mm"],
            "Trên (mm)": d["upper_limit_mm"], "Đo được (mm)": d["measured_mm"],
            "Độ lệch (mm)": d["deviation_mm"], "Kết luận": d["status"],
            "Gần giới hạn": d["near_limit"], "Chi tiết": d["reason"],
        } for d in dimensions]), hide_index=True, alt="Giới hạn, số đo chưa làm tròn và kết luận từng chiều")
    for message in record["warnings"]:
        st.warning(message)
    left, right = st.columns(2)
    with left:
        st.caption("Ảnh nguồn đã lưu")
        try:
            image = decode_image(outcome.source_bytes)
            st.image(image, channels="BGR", width="stretch", alt="Ảnh nguồn của lượt đo đã chọn")
        except VisionGaugeError:
            st.info("Ảnh nguồn không giải mã được; lỗi đã được ghi trong lượt đo.")
    with right:
        st.caption("Ảnh sau khử méo và chú thích kích thước")
        if outcome.annotated_png:
            st.image(outcome.annotated_png, width="stretch", alt="Bàn cờ và sản phẩm sau khử méo có chú thích kích thước")
            st.download_button("Tải ảnh chú thích", outcome.annotated_png,
                               file_name=f"{record['run_id']}.png", mime="image/png", key=f"{key}_png")
        else:
            st.info("Không có ảnh kết quả cho lượt đo thất bại.")
    st.caption("Kết luận dùng số đo chưa làm tròn. Cảnh báo gần giới hạn không tự thay đổi kết luận; chưa xét độ không đảm bảo đo.")
    with st.expander("Thông tin truy vết và các bước xử lý"):
        st.json(record)
