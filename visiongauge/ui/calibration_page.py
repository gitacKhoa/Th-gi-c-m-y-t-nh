"""Dedicated camera calibration and paired evaluation page."""

from hashlib import sha256

import pandas as pd
import streamlit as st

from visiongauge.calibration import (
    CameraCalibration, calibration_from_json, calibration_to_json,
    ChessboardDetection, chessboard_points_mm, draw_chessboard,
)
from visiongauge.config import ChessboardConfig, ConfigurationError, load_config
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image
from visiongauge.measurement.comparison import compare_measurements, read_references_csv, summarize_comparison
from .calibration_workflow import CalibrationWorkflow
from .calibration_capture import render_camera_capture


def _activate(calibration: CameraCalibration) -> None:
    st.session_state.active_calibration = calibration
    st.session_state.measurement_calibration_requested = True
    if "measurement_workflow" in st.session_state:
        st.session_state.measurement_workflow.clear()


def _show_model(calibration: CameraCalibration, key: str) -> None:
    st.write(f"{len(calibration.view_names)} ảnh · {calibration.image_size[0]} × {calibration.image_size[1]} px · ID {calibration.fingerprint[:12]}")
    st.metric("Reprojection RMS (px)", f"{calibration.rms_px:.4f}")
    st.caption("RMS là sai số khớp các góc dùng để hiệu chuẩn; không phải độ chính xác đo kích thước độc lập.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Camera matrix (K)**")
        st.dataframe(calibration.camera_matrix)
    with right:
        st.markdown("**Distortion coefficients**")
        st.dataframe(pd.DataFrame({"hệ số": ["k1", "k2", "p1", "p2", "k3"], "giá trị": calibration.distortion}), hide_index=True)
    st.dataframe(pd.DataFrame({"ảnh": calibration.view_names, "RMSE (px)": calibration.per_view_rmse_px}), hide_index=True)
    with st.expander("Rotation / Translation vectors"):
        st.caption("rvec: Rodrigues (radian); tvec: mm, hệ tọa độ bàn cờ → camera, riêng cho mỗi ảnh.")
        st.dataframe(pd.DataFrame({
            "ảnh": calibration.view_names,
            **{f"r{i}": calibration.rvecs[:, i] for i in range(3)},
            **{f"t{i} (mm)": calibration.tvecs[:, i] for i in range(3)},
        }), hide_index=True)
    st.download_button("Lưu calibration JSON", calibration_to_json(calibration),
                       file_name="visiongauge_calibration.json", mime="application/json", key=f"download_{key}")
    acceptable = calibration.rms_px <= 1.0 and max(calibration.per_view_rmse_px) <= 2.0
    if not acceptable:
        st.warning("Calibration vượt ngưỡng ứng dụng (RMS tổng 1 px hoặc từng ảnh 2 px); cần hiệu chuẩn lại trước khi áp dụng.")
    if st.button("Áp dụng cho chức năng đo", key=f"apply_{key}", type="primary", disabled=not acceptable):
        _activate(calibration)
        st.success("Đã áp dụng. Chọn trang Đo kích thước; ảnh đầu vào phải từ cùng camera, độ phân giải và thiết lập ống kính.")


def _comparison_page(board: ChessboardConfig) -> None:
    st.subheader("So sánh trước / sau trên cùng ảnh")
    st.caption("Ảnh thô là baseline cố ý bỏ qua méo; không dùng kết quả đó để kiểm tra dung sai. Nhánh sau khử méo trước khi tính homography.")
    active = st.session_state.get("active_calibration")
    files = st.file_uploader("Ảnh sản phẩm để so sánh", type=["png", "jpg", "jpeg", "bmp"], accept_multiple_files=True, key="comparison_images")
    reference = st.file_uploader("Kích thước tham chiếu CSV (tùy chọn)", type=["csv"], key="comparison_reference")
    st.code("filename,length_mm,width_mm", language="text")
    st.caption("CSV dùng tên file chính xác, kích thước mm từ dụng cụ tham chiếu; không có CSV thì chỉ so sánh số đo, không tính độ chính xác.")
    data = [(file.name, file.getvalue()) for file in files]
    reference_bytes = reference.getvalue() if reference is not None else None
    signature = sha256(repr(([(name, sha256(value).hexdigest()) for name, value in data], vars(board),
                             active.fingerprint if active else None, reference_bytes)).encode()).hexdigest()
    if st.session_state.get("comparison_signature") != signature:
        st.session_state.comparison_signature = signature
        st.session_state.pop("comparison_table", None)
        st.session_state.pop("comparison_error", None)
    if active is None:
        st.info("Cần áp dụng calibration trước khi chạy so sánh.")
    if st.button("Chạy so sánh trước / sau", key="run_comparison", disabled=not data or active is None):
        st.session_state.pop("comparison_table", None)
        st.session_state.pop("comparison_error", None)
        try:
            references = read_references_csv(reference_bytes) if reference_bytes is not None else None
            with st.spinner("Đang đo cùng bộ ảnh trước và sau khử méo…"):
                st.session_state.comparison_table = compare_measurements(data, board, active, references)
        except VisionGaugeError as exc:
            st.session_state.comparison_error = str(exc)
    if st.session_state.get("comparison_error"):
        st.error(st.session_state.comparison_error)
    table = st.session_state.get("comparison_table")
    if table is not None:
        st.dataframe(table, hide_index=True)
        st.caption(f"Tổng {len(table)} ảnh · lỗi baseline {(table.raw_error != '').sum()} · lỗi sau hiệu chỉnh {(table.corrected_error != '').sum()}")
        summary = summarize_comparison(table)
        if summary.empty:
            st.info("Chưa có đủ cặp kết quả và số đo tham chiếu để đánh giá độ chính xác.")
        else:
            st.dataframe(summary, hide_index=True)
            st.caption("MAE/RMSE chỉ dùng các ảnh có tham chiếu và đo thành công ở cả hai nhánh; ảnh bị loại được đếm rõ trong bảng.")
        st.download_button("Tải bảng so sánh CSV", table.to_csv(index=False).encode("utf-8-sig"),
                           file_name="visiongauge_before_after.csv", mime="text/csv", key="download_comparison")


def render_calibration_page() -> None:
    st.header("Camera Calibration")
    st.caption("Một camera, một độ phân giải và một thiết lập zoom/focus. Khuyến nghị 15–25 ảnh, thay đổi vị trí và nghiêng bàn cờ theo nhiều hướng.")
    try:
        defaults = load_config().chessboard
    except ConfigurationError as exc:
        st.error(f"Lỗi cấu hình: {exc}")
        return
    with st.sidebar:
        st.subheader("Bàn cờ hiệu chuẩn / so sánh")
        columns = st.number_input("Góc trong theo chiều ngang", min_value=3, value=defaults.columns, step=1, key="cal_columns")
        rows = st.number_input("Góc trong theo chiều dọc", min_value=3, value=defaults.rows, step=1, key="cal_rows")
        size = st.number_input("Cạnh ô vuông hiệu chuẩn (mm)", min_value=0.0, value=float(defaults.square_size_mm), key="cal_square_size")
        active = st.session_state.get("active_calibration")
        if active is not None:
            st.caption(f"Đang áp dụng calibration {active.fingerprint[:12]}")
            if st.button("Gỡ calibration đang áp dụng", key="clear_calibration"):
                st.session_state.pop("active_calibration", None)
                st.session_state.pop("measurement_calibration_requested", None)
                if "measurement_workflow" in st.session_state:
                    st.session_state.measurement_workflow.clear()
                st.rerun()
    try:
        board = ChessboardConfig(columns, rows, size)
    except ConfigurationError as exc:
        st.session_state.pop("calibration_workflow", None)
        st.error(f"Thông số bàn cờ không hợp lệ: {exc}")
        return
    fit_tab, load_tab, compare_tab = st.tabs(["Hiệu chuẩn từ ảnh", "Nạp calibration", "So sánh trước / sau"])
    with fit_tab:
        source = st.radio("Nguồn ảnh hiệu chuẩn", ["Upload ảnh", "Chụp camera"], horizontal=True, key="calibration_source")
        if source == "Chụp camera":
            images = render_camera_capture()
        else:
            uploads = st.file_uploader("Upload nhiều ảnh Chessboard", type=["png", "jpg", "jpeg", "bmp"],
                                       accept_multiple_files=True, key="calibration_images")
            images = [(file.name, file.getvalue()) for file in uploads]
        if "calibration_workflow" not in st.session_state:
            st.session_state.calibration_workflow = CalibrationWorkflow()
        workflow = st.session_state.calibration_workflow
        workflow.update(images, board)
        detect, fit = st.columns(2)
        with detect:
            if st.button("Kiểm tra ảnh bàn cờ", key="scan_calibration", disabled=not images):
                with st.spinner("Đang tìm và tinh chỉnh các góc bàn cờ…"):
                    workflow.detect(images, board)
        with fit:
            if st.button("Chạy hiệu chuẩn", key="fit_calibration", disabled=not images, type="primary"):
                with st.spinner("Đang hiệu chuẩn camera…"):
                    workflow.calibrate(images, board)
        if workflow.error:
            st.error(workflow.error)
        if workflow.scan is not None:
            good, bad = st.columns(2)
            good.metric("Ảnh nhận diện thành công", len(workflow.scan.views))
            bad.metric("Ảnh thất bại / bị loại", len(workflow.scan.failures))
            st.dataframe(pd.DataFrame(
                [(v.name, "Đủ góc") for v in workflow.scan.views] + list(workflow.scan.failures), columns=["ảnh", "trạng thái"],
            ), hide_index=True)
            if workflow.scan.views:
                name = st.selectbox("Xem góc bàn cờ đã nhận diện", [v.name for v in workflow.scan.views], key="calibration_preview")
                view = next(v for v in workflow.scan.views if v.name == name)
                detection = ChessboardDetection(view.corners_px, chessboard_points_mm(board), board, "calibration")
                st.image(draw_chessboard(decode_image(dict(images)[name]), detection), channels="BGR", width="stretch")
        if workflow.result is not None:
            _show_model(workflow.result, "generated_calibration")
    with load_tab:
        uploaded = st.file_uploader("Nạp file calibration JSON", type=["json"], key="calibration_json")
        payload = uploaded.getvalue() if uploaded is not None else None
        digest = sha256(payload).hexdigest() if payload is not None else None
        if st.session_state.get("loaded_calibration_digest") != digest:
            st.session_state.loaded_calibration_digest = digest
            st.session_state.pop("loaded_calibration", None)
            st.session_state.pop("loaded_calibration_error", None)
        if st.button("Nạp calibration", key="load_calibration", disabled=payload is None):
            st.session_state.pop("loaded_calibration", None)
            st.session_state.pop("loaded_calibration_error", None)
            try:
                st.session_state.loaded_calibration = calibration_from_json(payload)
            except VisionGaugeError as exc:
                st.session_state.loaded_calibration_error = str(exc)
        if st.session_state.get("loaded_calibration_error"):
            st.error(st.session_state.loaded_calibration_error)
        if st.session_state.get("loaded_calibration") is not None:
            _show_model(st.session_state.loaded_calibration, "loaded_calibration")
    with compare_tab:
        _comparison_page(board)
