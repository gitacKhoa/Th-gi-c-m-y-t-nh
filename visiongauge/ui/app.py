"""Streamlit measurement workspace, backed by the existing headless pipeline."""

import streamlit as st

from visiongauge import __version__
from visiongauge.config import ChessboardConfig, ConfigurationError, load_config
from .views import render_debug, render_results, render_status
from .workflow import MeasurementWorkflow
from .tolerance_panel import render_tolerance_controls, render_tolerance_result


GEOMETRY_CHOICES = {
    "Chưa xác nhận": None,
    "Ảnh đã khử méo / ảnh tổng hợp": "undistorted",
    "Méo ống kính không đáng kể": "negligible_distortion",
    "Dùng calibration đang áp dụng": "calibrated",
}
SEGMENTATION_CHOICES = {"Threshold · Otsu": "threshold", "Canny": "canny"}


def main() -> None:
    st.set_page_config(page_title="VisionGauge — Đo kích thước", page_icon="📐", layout="wide")
    st.markdown(
        """<style>
        .block-container {max-width: 1440px; padding-top: 2rem; padding-bottom: 2rem;}
        h1 {letter-spacing: -0.04em;}
        [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
        @media (max-width: 700px) {
            .block-container {padding: 1rem;}
            [data-testid="stHorizontalBlock"] {flex-wrap: wrap;}
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                min-width: 100% !important; width: 100% !important; flex: 1 1 100% !important;
            }
        }
        </style>""", unsafe_allow_html=True,
    )
    st.title("VisionGauge")
    st.caption(f"Đo kích thước không tiếp xúc · Chessboard · v{__version__}")
    page = st.sidebar.radio("Trang", ["Đo kích thước", "Quy trình đo", "Camera Calibration", "Lịch sử"], key="app_page")
    if page == "Quy trình đo":
        from .inspection_page import render_inspection_page
        render_inspection_page()
        return
    if page == "Lịch sử":
        from .history_page import render_history_page
        render_history_page()
        return
    if page == "Camera Calibration":
        from .calibration_page import render_calibration_page
        render_calibration_page()
        return
    st.info("Trang này dùng xem trước và debug thuật toán. Để đo có calibration bắt buộc, lưu lịch sử và xuất báo cáo, chọn trang Quy trình đo.")
    if st.session_state.pop("measurement_calibration_requested", False):
        st.session_state["image_geometry"] = "Dùng calibration đang áp dụng"

    if "measurement_workflow" not in st.session_state:
        st.session_state.measurement_workflow = MeasurementWorkflow()
    workflow = st.session_state.measurement_workflow
    try:
        config = load_config()
    except ConfigurationError as exc:
        workflow.clear()
        st.error(f"Lỗi cấu hình: {exc}")
        st.stop()

    with st.sidebar:
        st.header("Cấu hình bàn cờ")
        st.caption("Đếm góc trong, không phải số ô vuông.")
        columns = st.number_input(
            "Số góc trong theo chiều ngang", min_value=3, value=config.chessboard.columns,
            step=1, key="board_columns", help="Số cột góc trong của bàn cờ.",
        )
        rows = st.number_input(
            "Số góc trong theo chiều dọc", min_value=3, value=config.chessboard.rows,
            step=1, key="board_rows", help="Số hàng góc trong của bàn cờ.",
        )
        size = st.number_input(
            "Cạnh ô vuông (mm)", min_value=0.0, value=float(config.chessboard.square_size_mm),
            step=0.1, format="%.4f", key="square_size",
        )
        st.caption(f"{columns} × {rows} góc trong · {size:g} mm/ô")
        st.caption("Đặt bàn cờ cùng mặt phẳng với sản phẩm. Thay đổi chỉ áp dụng trong phiên này.")
        st.divider()
        geometry_label = st.selectbox("Điều kiện méo ảnh", list(GEOMETRY_CHOICES), key="image_geometry")
        active = st.session_state.get("active_calibration")
        if active is not None:
            st.caption(f"Calibration sẵn có: {active.image_size[0]} × {active.image_size[1]} px · RMS {active.rms_px:.3f} px")
        st.caption("Chế độ dùng calibration tự khử méo ảnh đầu vào. Các lựa chọn khác chỉ xác nhận điều kiện ảnh. Homography không thay thế hiệu chỉnh méo ống kính.")
        with st.expander("Tùy chọn xử lý"):
            segmentation_label = st.selectbox("Tách đường viền", list(SEGMENTATION_CHOICES), key="segmentation")

    with st.sidebar:
        tolerance_controls = render_tolerance_controls()

    try:
        board = ChessboardConfig(columns=columns, rows=rows, square_size_mm=size)
    except ConfigurationError as exc:
        workflow.clear()
        st.error(f"Thông số bàn cờ không hợp lệ: {exc}")
        st.stop()

    with st.container(border=True):
        st.subheader("Ảnh đầu vào")
        source = st.radio("Nguồn ảnh", ["Tải ảnh", "Chụp camera"], horizontal=True, key="image_source")
        if source == "Tải ảnh":
            uploaded = st.file_uploader(
                "Chọn ảnh sản phẩm và bàn cờ", type=["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"],
                key="uploaded_image", help="Một sản phẩm chữ nhật phẳng và toàn bộ các góc trong bàn cờ. Ảnh 8-bit, tối đa 20 MB.",
            )
        else:
            st.caption("Chụp một ảnh tĩnh. Cho phép trình duyệt truy cập camera; dùng localhost hoặc HTTPS. Nếu camera không khả dụng, chọn Tải ảnh.")
            capture_resolution = "720p"
            if GEOMETRY_CHOICES[geometry_label] == "calibrated" and active is not None:
                target_width, target_height = active.image_size
                capture_resolution = {480: "480p", 720: "720p", 1080: "1080p"}.get(target_height, "720p")
                st.info(
                    f"Calibration cần ảnh {target_width} × {target_height} px. "
                    f"Camera được yêu cầu chụp {capture_resolution}; kích thước thực tế còn phụ thuộc camera và trình duyệt. "
                    "Nếu không khớp, tải ảnh gốc đúng chế độ chụp hoặc hiệu chuẩn lại bằng ảnh từ cùng nguồn camera."
                )
            st.caption(f"Mức chụp yêu cầu: {capture_resolution}, không phụ thuộc chiều rộng hiển thị của widget.")
            uploaded = st.camera_input("Chụp sản phẩm và bàn cờ", key="camera_image", resolution=capture_resolution)
        payload = uploaded.getvalue() if uploaded is not None else None

    workflow.update_input(
        payload, board, source=source, image_geometry=GEOMETRY_CHOICES[geometry_label],
        segmentation=SEGMENTATION_CHOICES[segmentation_label],
        calibration=active if GEOMETRY_CHOICES[geometry_label] == "calibrated" else None,
    )
    if (
        GEOMETRY_CHOICES[geometry_label] == "calibrated" and active is not None
        and workflow.raw_image is not None
        and workflow.raw_image.shape[1::-1] != active.image_size
    ):
        st.warning(
            "Ảnh đọc được nhưng chưa tương thích với calibration. "
            "Hãy chụp lại cùng camera, độ phân giải, tỉ lệ khung hình và thiết lập zoom/focus của bộ hiệu chuẩn, "
            "rồi chọn Tải ảnh để dùng file gốc; hoặc tạo calibration mới cho chế độ chụp hiện tại. "
            "Không kéo giãn/cắt ảnh để ép khớp kích thước, và không chọn 'Ảnh đã khử méo' để bỏ qua lỗi."
        )
    detect_column, measure_column = st.columns(2)
    with detect_column:
        if st.button("Phát hiện bàn cờ", key="detect_board", disabled=workflow.image is None, width="stretch"):
            with st.spinner("Đang tìm các góc bàn cờ…"):
                workflow.detect()
    with measure_column:
        if st.button(
            "Bắt đầu đo", key="start_measurement", type="primary", width="stretch",
            disabled=workflow.image is None or workflow.image_geometry is None,
        ):
            with st.spinner("Đang xử lý ảnh và đo sản phẩm…"):
                workflow.measure()
    if workflow.image is None and workflow.input_error is None:
        st.info("Tải ảnh hoặc chụp ảnh để bắt đầu. Cấu hình bàn cờ phải khớp với mẫu thực tế.")
    elif workflow.image_geometry is None:
        st.info("Có thể phát hiện bàn cờ ngay. Để đo, hãy xác nhận điều kiện méo ảnh ở thanh cấu hình.")

    render_status(workflow)
    render_results(workflow)
    render_tolerance_result(workflow, tolerance_controls)
    if st.toggle("Xem các bước xử lý ảnh (debug)", key="show_debug"):
        render_debug(workflow)
