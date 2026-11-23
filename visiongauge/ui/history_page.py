"""Saved history, exact snapshot review, and CSV/PDF downloads."""

from hashlib import sha256
import json

import streamlit as st

from visiongauge.reporting import records_to_csv, records_to_pdf
from visiongauge.storage import HistoryError, HistoryStore
from visiongauge.workflow.models import PASS, FAIL, NOT_EVALUABLE
from .run_views import render_counts, records_table, render_run_detail


@st.cache_data(max_entries=8, ttl=300, show_spinner=False)
def _pdf(records, annotated_images=None):
    return records_to_pdf(records, annotated_images=annotated_images)


def render_history_page() -> None:
    st.header("Lịch sử phép đo")
    st.caption("Kết quả bất biến theo cấu hình tại thời điểm đo. Đổi cấu hình hiện tại không thay đổi kết luận đã lưu.")
    store = HistoryStore()
    try:
        records = store.list_records()
    except HistoryError as exc:
        st.error(f"LỖI ĐỌC LỊCH SỬ: {exc}")
        return
    if not records:
        st.info("Chưa có lượt đo đã lưu. Mở trang Quy trình đo để bắt đầu.")
        return
    status = st.selectbox("Lọc kết luận", ["Tất cả", PASS, FAIL, NOT_EVALUABLE], key="history_status")
    product = st.text_input("Lọc mã sản phẩm (chứa chuỗi)", key="history_product")
    dates = sorted({r["started_at"][:10] for r in records})
    selected_date = st.selectbox("Ngày đo (UTC)", ["Tất cả", *reversed(dates)], key="history_date")
    filtered = [r for r in records if (status == "Tất cả" or r["decision"] == status)
                and product.casefold() in r["product_id"].casefold()
                and (selected_date == "Tất cả" or r["started_at"][:10] == selected_date)]
    render_counts(filtered)
    if not filtered:
        st.info("Không có lượt đo khớp bộ lọc.")
        return
    st.caption(f"Có {len(filtered)} lượt khớp bộ lọc. Bảng hiển thị tối đa 200 lượt mới nhất; CSV xuất toàn bộ kết quả khớp.")
    st.dataframe(records_table(filtered[:200]), hide_index=True, alt="Lịch sử đã lọc với mã lượt đo, kết luận và mã lỗi")
    st.download_button("Xuất CSV theo bộ lọc", records_to_csv(filtered), file_name="visiongauge_history.csv",
                       mime="text/csv", key="history_csv")
    signature = sha256(json.dumps(filtered, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if len(filtered) > 200:
        st.info("PDF hỗ trợ tối đa 200 lượt mỗi báo cáo; thu hẹp bộ lọc để xuất PDF.")
    if st.button("Tạo PDF theo bộ lọc", key="history_create_pdf", disabled=len(filtered) > 200):
        try:
            with st.spinner("Đang tạo báo cáo PDF…"):
                st.session_state.history_pdf = (signature, _pdf(filtered))
        except Exception as exc:
            st.session_state.pop("history_pdf", None)
            st.error(f"LỖI XUẤT PDF: {exc}. Lịch sử đã lưu vẫn còn nguyên.")
    export = st.session_state.get("history_pdf")
    if export is not None and export[0] == signature:
        st.download_button("Tải PDF theo bộ lọc", export[1], file_name="visiongauge_history.pdf",
                           mime="application/pdf", key="history_pdf_download")

    labels = {r["run_id"]: f"{r['started_at']} · {r['product_id']} · {r['filename']} · {r['run_id'][:8]}" for r in filtered}
    chosen = st.selectbox("Xem chi tiết lượt đo", list(labels), format_func=labels.get, key="history_detail")
    try:
        outcome = store.get(chosen)
    except HistoryError as exc:
        st.error(str(exc))
        return
    render_run_detail(outcome, key="history_selected")
    st.download_button("Tải cấu hình và kết quả JSON", json.dumps(outcome.record, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name=f"{chosen}.json", mime="application/json", key="history_json")
    if st.button("Tạo PDF chi tiết có ảnh", key="history_detail_pdf"):
        try:
            pictures = {chosen: outcome.annotated_png} if outcome.annotated_png else None
            st.session_state.history_detail_report = (chosen, _pdf([outcome.record], pictures))
        except Exception as exc:
            st.session_state.pop("history_detail_report", None)
            st.error(f"LỖI XUẤT PDF: {exc}")
    detail_report = st.session_state.get("history_detail_report")
    if detail_report is not None and detail_report[0] == chosen:
        st.download_button("Tải PDF chi tiết", detail_report[1], file_name=f"{chosen}.pdf",
                           mime="application/pdf", key="history_detail_pdf_download")
