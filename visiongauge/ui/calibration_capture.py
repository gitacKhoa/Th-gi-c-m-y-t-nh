"""Capture, review and export a calibration dataset from the browser camera."""

import streamlit as st

from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image
from .capture_workflow import CalibrationCaptures


def render_camera_capture() -> list[tuple[str, bytes]]:
    if "calibration_captures" not in st.session_state:
        st.session_state.calibration_captures = CalibrationCaptures()
    captures = st.session_state.calibration_captures
    presets = ["480p", "720p", "1080p"]
    resolution = st.selectbox(
        "Mức chụp ảnh hiệu chuẩn", presets, index=presets.index(captures.resolution),
        key="calibration_capture_resolution", disabled=bool(captures.images),
    )
    captures.resolution = resolution
    st.caption(
        "Cho phép trình duyệt truy cập camera (localhost hoặc HTTPS). "
        "Chụp rồi bấm Thêm ảnh vào bộ hiệu chuẩn; thay đổi vị trí và nghiêng bàn cờ trước ảnh tiếp theo. "
        "Giữ nguyên camera, zoom/focus và chế độ chụp trong cả bộ ảnh."
    )
    st.caption(
        "Mức chụp là yêu cầu tới camera; kích thước ảnh thực tế được kiểm tra khi thêm. "
        "Cần ít nhất 5 ảnh nhận diện đủ góc, khuyến nghị 15–25 ảnh đa dạng góc chụp."
    )
    snapshot = st.camera_input(
        "Chụp bàn cờ hiệu chuẩn", resolution=resolution,
        key=f"calibration_camera_{captures.widget_generation}",
    )
    if st.button("Thêm ảnh vào bộ hiệu chuẩn", key="add_calibration_capture", disabled=snapshot is None):
        try:
            captures.add(snapshot.getvalue())
        except VisionGaugeError as exc:
            st.error(str(exc))
        else:
            st.rerun()  # New widget key clears the accepted photo, ready for the next shot.

    st.write(f"Đã lưu trong phiên: **{len(captures.images)} ảnh**")
    if captures.image_size is not None:
        width, height = captures.image_size
        st.caption(f"Độ phân giải thực tế: {width} × {height} px. Ảnh đo sau này phải dùng cùng chế độ chụp.")
    st.caption("Ảnh chỉ được giữ trong phiên. Tải ZIP để lưu lại trước khi đóng hoặc tải lại trang trình duyệt.")
    if captures.images:
        selected = st.selectbox("Xem ảnh đã chụp", [name for name, _ in captures.images], key="capture_preview")
        with st.expander("Ảnh chụp đã lưu", expanded=False):
            st.image(decode_image(dict(captures.images)[selected]), channels="BGR", width="stretch")
        remove, clear = st.columns(2)
        with remove:
            if st.button("Xóa ảnh đang chọn", key="remove_calibration_capture"):
                captures.remove(selected)
                st.rerun()
        with clear:
            if st.button("Xóa bộ ảnh đã chụp", key="clear_calibration_captures"):
                captures.clear()
                st.rerun()
        st.download_button(
            "Tải bộ ảnh đã chụp (ZIP)", captures.archive(), file_name="visiongauge_calibration_photos.zip",
            mime="application/zip", key="download_calibration_captures", on_click="ignore",
        )
    return list(captures.images)
