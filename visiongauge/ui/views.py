"""Presentation components; no measurement logic is implemented here."""

import cv2
import pandas as pd
import streamlit as st

from visiongauge.calibration import estimate_planar_mapping
from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import to_gray
from visiongauge.processing import ContourOptions, extract_product_contours
from .workflow import MeasurementWorkflow


def render_status(workflow: MeasurementWorkflow) -> None:
    image_status = "Ảnh không hợp lệ" if workflow.input_error else ("Đã nhận ảnh" if workflow.image is not None else "Chờ ảnh")
    if workflow.input_error and workflow.raw_image is not None:
        image_status = "Chưa phù hợp điều kiện đo"
    board_status = "Không tìm thấy / chưa hợp lệ" if workflow.board_error else (
        f"Đã tìm đủ {len(workflow.detection.corners_px)} góc" if workflow.detection is not None else "Chưa phát hiện"
    )
    processing_status = "Không thể đo" if workflow.measurement_error or workflow.board_error else (
        "Đo hoàn tất" if workflow.result is not None else "Chưa đo"
    )
    for column, label, value in zip(
        st.columns(3), ("ẢNH ĐẦU VÀO", "BÀN CỜ", "XỬ LÝ"), (image_status, board_status, processing_status),
    ):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"**{value}**")


def render_results(workflow: MeasurementWorkflow) -> None:
    if workflow.result is not None:
        st.success("Đo hoàn tất. Kích thước được tính trong mặt phẳng mm của bàn cờ.")
    for error in (workflow.input_error, workflow.board_error, workflow.measurement_error):
        if error:
            st.error(f"KHÔNG THỂ ĐÁNH GIÁ: {error}")
    length, width = st.columns(2)
    with length:
        st.metric("Chiều dài (mm)", f"{workflow.result.length_mm:.2f}" if workflow.result else "—", border=True)
    with width:
        st.metric("Chiều rộng (mm)", f"{workflow.result.width_mm:.2f}" if workflow.result else "—", border=True)
    original, processed = st.columns(2, gap="medium")
    with original:
        with st.container(border=True):
            st.markdown("**Ảnh gốc**")
            original_image = workflow.raw_image if workflow.raw_image is not None else workflow.image
            if original_image is not None:
                st.image(original_image, channels="BGR", width="stretch")
                height, width = original_image.shape[:2]
                st.caption(f"{width} × {height} px · Đo trên độ phân giải gốc")
            else:
                st.caption("Tải ảnh hoặc chụp một ảnh để bắt đầu.")
    with processed:
        with st.container(border=True):
            st.markdown("**Ảnh kết quả**")
            if workflow.result is not None:
                st.image(workflow.result.annotated_image, channels="BGR", width="stretch")
                st.caption("Các góc bàn cờ, đường bao và kích thước sản phẩm.")
            elif workflow.board_preview is not None:
                st.image(workflow.board_preview, channels="BGR", width="stretch")
                st.caption("Đã đánh dấu các góc bàn cờ. Chưa có kết quả đo sản phẩm.")
            else:
                st.caption("Kết quả phát hiện bàn cờ hoặc đo sẽ xuất hiện tại đây.")
    if workflow.result is not None and workflow.result_png is not None:
        if workflow.calibration_id:
            st.caption(f"Đã khử méo trước khi đo · Calibration {workflow.calibration_id[:12]} · Ảnh kết quả nằm trong hệ tọa độ đã khử méo.")
        st.download_button(
            "Tải ảnh kết quả (PNG)", workflow.result_png, file_name="visiongauge_measurement.png",
            mime="image/png", key="download_result", on_click="ignore",
        )
        for warning in workflow.result.warnings:
            st.caption(warning)
        st.caption("Số lẻ hiển thị không biểu thị độ chính xác đã kiểm chứng. Chưa phân loại dung sai.")


def render_debug(workflow: MeasurementWorkflow) -> None:
    """Show the same grayscale/blur settings and actual mask used by the pipeline."""
    if workflow.image is None:
        return
    with st.expander("Các bước xử lý ảnh", expanded=True):
        if workflow.calibration_id:
            st.caption("0 · Ảnh đã khử méo (cùng độ phân giải và camera matrix)")
            st.image(workflow.image, channels="BGR", width="stretch")
        options = ContourOptions(method=workflow.segmentation)
        gray = to_gray(workflow.image)
        blurred = cv2.GaussianBlur(gray, (options.blur_kernel, options.blur_kernel), 0)
        for column, image, title in zip(st.columns(2), (gray, blurred), ("1 · Grayscale", "2 · Gaussian Blur (5 × 5)")):
            with column:
                st.caption(title)
                st.image(image, width="stretch", clamp=True)
        if workflow.detection is not None:
            st.caption(f"Góc bàn cờ: {workflow.detection.method.upper()} · tọa độ trong ảnh đầu vào")
            st.dataframe(pd.DataFrame(workflow.detection.corners_px, columns=["x (px)", "y (px)"]), hide_index=True)
        mapping = workflow.result.mapping if workflow.result is not None else None
        mask = workflow.result.segmentation_mask if workflow.result is not None else None
        if mapping is None and workflow.detection is not None:
            try:
                mapping = estimate_planar_mapping(workflow.detection.corners_px, workflow.detection.config)
                segmented = extract_product_contours(workflow.image, mapping, options)
                mask = segmented.mask
                st.caption(f"Contours sau khi loại nhiễu/bàn cờ: {len(segmented.contours_px)} · chưa kiểm tra hình chữ nhật trong mm.")
            except (VisionGaugeError, cv2.error) as exc:
                st.warning(f"Chưa tạo được dữ liệu debug ánh xạ: {exc}")
        if mask is not None and mapping is not None:
            st.caption(f"3 · Mask thực tế ({workflow.segmentation})")
            st.image(mask, width="stretch", clamp=True)
            st.caption("Bàn cờ được loại ở bước lọc contours, nên vẫn có thể xuất hiện trong mask.")
            quality = mapping.quality
            st.write(f"Chiếu lại bàn cờ: RMSE {quality.rmse_px:.3f} px · lỗi lớn nhất {quality.max_error_px:.3f} px")
            st.caption("Homography: tọa độ ảnh → tọa độ mặt phẳng mm")
            st.dataframe(mapping.image_to_mm)
        else:
            st.caption("Cần bàn cờ hợp lệ để kiểm tra mask lọc contours và homography.")
