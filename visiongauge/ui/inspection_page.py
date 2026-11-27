"""Production flow: explicit batch/camera attempts, calibrated inspection, save."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json

import streamlit as st

from visiongauge.calibration import calibration_from_json
from visiongauge.config import ChessboardConfig, ConfigurationError, load_config
from visiongauge.errors import VisionGaugeError
from visiongauge.storage import HistoryStore, HistoryError
from visiongauge.workflow import InspectionSettings, QualityOptions, inspect_batch
from visiongauge.image_io import decode_image
from .run_views import render_counts, render_run_detail, records_table
from .tolerance_panel import render_tolerance_controls


def _save_pending(store):
    pending = st.session_state.get("flow_pending", [])
    remaining = []
    errors = []
    for outcome in pending:
        try:
            store.save(outcome)
        except HistoryError as exc:
            remaining.append(outcome)
            errors.append(str(exc))
    st.session_state.flow_pending = remaining
    st.session_state.flow_storage_errors = list(dict.fromkeys(errors))


def render_inspection_page() -> None:
    st.header("Quy trình đo sản phẩm")
    st.caption("Ảnh → calibration → chất lượng → Chessboard → đo mm → dung sai → lịch sử. Mỗi lần nhấn đo tạo mã lượt đo mới.")
    st.session_state.setdefault("flow_pending", [])
    store = HistoryStore()
    if st.session_state.flow_pending:
        st.error(f"LỖI LƯU TRỮ: {len(st.session_state.flow_pending)} lượt chưa lưu. Giữ phiên này và thử lưu lại; chưa chạy lô mới.")
        for error in st.session_state.get("flow_storage_errors", []):
            st.error(error)
        if st.button("Thử lưu lại lịch sử", key="retry_history"):
            _save_pending(store)
            st.rerun()
    try:
        default_board = load_config().chessboard
    except ConfigurationError as exc:
        st.error(str(exc))
        return
    with st.sidebar:
        st.subheader("Bàn cờ đo sản phẩm")
        columns = st.number_input("Góc trong ngang", min_value=3, value=default_board.columns, key="flow_columns", persist_state="session")
        rows = st.number_input("Góc trong dọc", min_value=3, value=default_board.rows, key="flow_rows", persist_state="session")
        size = st.number_input("Cạnh ô (mm)", min_value=0., value=float(default_board.square_size_mm), key="flow_square", persist_state="session")
        controls = render_tolerance_controls(required=True)
        with st.expander("Ngưỡng chất lượng và cảnh báo"):
            st.caption("Ngưỡng sàng lọc cần được xác minh với bộ ảnh thực tế; không phải độ chính xác theo mm.")
            sharpness = st.number_input("Laplacian variance tối thiểu", min_value=.1, value=20., key="flow_sharpness", persist_state="session")
            contrast = st.number_input("Tương phản P95-P05 tối thiểu", min_value=.1, max_value=255., value=20., key="flow_contrast", persist_state="session")
            near = st.number_input("Cảnh báo cách giới hạn ≤ (mm)", min_value=0., value=.2, key="flow_near", persist_state="session")
            method = st.selectbox("Tách đường viền", ["threshold", "canny"], key="flow_method", persist_state="session")
    try:
        board = ChessboardConfig(columns, rows, size)
        quality = QualityOptions(sharpness, contrast)
    except ValueError as exc:
        st.warning(f"KHÔNG THỂ ĐÁNH GIÁ: {exc}")
        return
    if controls.error:
        st.warning(controls.error)

    with st.container(border=True):
        st.subheader("Calibration và điều kiện đo")
        calibration_file = st.file_uploader("Nạp calibration JSON cho lượt đo (tùy chọn nếu đã áp dụng)", type=["json"], key="flow_calibration")
        calibration = st.session_state.get("active_calibration")
        calibration_error = None
        if calibration_file is not None:
            try:
                calibration = calibration_from_json(calibration_file.getvalue())
            except VisionGaugeError as exc:
                calibration = None
                calibration_error = str(exc)
                st.error(calibration_error)
        if calibration is None:
            st.warning("Chưa có calibration hợp lệ. Tạo tại Camera Calibration hoặc nạp JSON; lượt đo sẽ không được đánh giá khi thiếu calibration.")
        else:
            st.info(f"Calibration {calibration.fingerprint[:12]} · {calibration.image_size[0]} × {calibration.image_size[1]} px · RMS {calibration.rms_px:.4f} px")
        confirmed = st.checkbox(
            "Tất cả ảnh dùng đúng camera/độ phân giải/zoom/focus đã hiệu chuẩn; bàn cờ đúng kích thước, phẳng và đồng phẳng với sản phẩm; đủ góc nhìn thấy rõ.",
            key="flow_conditions",
        )
        product = st.text_input("Mã sản phẩm", max_chars=120, key="flow_product", persist_state="session")
        notes = st.text_area("Điều kiện chụp / ghi chú", max_chars=2000, key="flow_notes", persist_state="session")

    source = st.segmented_control("Nguồn ảnh", ["File", "Camera"], default="File", required=True, key="flow_source")
    if source == "Camera":
        height = calibration.image_size[1] if calibration is not None else 720
        resolution = {480: "480p", 720: "720p", 1080: "1080p"}.get(height, "720p")
        st.caption(f"Yêu cầu camera {resolution}; ảnh thực vẫn phải khớp calibration. Chụp và đo từng ảnh, rồi chụp ảnh tiếp theo.")
        image = st.camera_input("Chụp sản phẩm và bàn cờ", key="flow_camera", resolution=resolution)
        images = [(image.name, image.getvalue())] if image is not None else []
        if image is not None:
            # Keep and download the exact bytes returned by the camera widget.  Do
            # not decode/re-encode the image: that would change the dataset source.
            image_bytes = image.getvalue()
            decoded = decode_image(image_bytes)
            height_px, width_px = decoded.shape[:2]
            stem = image.name.rsplit(".", 1)[0] or "capture"
            metadata = {
                "filename": image.name,
                "width_px": width_px,
                "height_px": height_px,
                "bytes": len(image_bytes),
                "sha256": sha256(image_bytes).hexdigest(),
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "product_id": product,
                "notes": notes,
                "camera_resolution": resolution,
                "calibration_fingerprint": calibration.fingerprint if calibration else None,
            }
            with st.container(border=True):
                st.subheader("Lưu ảnh vừa chụp")
                st.caption(
                    f"Ảnh gốc {width_px} × {height_px} px · {len(image_bytes):,} bytes. "
                    "File tải xuống giữ nguyên bytes, không resize hoặc nén lại."
                )
                col_image, col_meta = st.columns(2)
                with col_image:
                    st.download_button(
                        "Tải ảnh gốc",
                        data=image_bytes,
                        file_name=image.name,
                        mime=image.type or "image/jpeg",
                        key="download_captured_image",
                        width="stretch",
                    )
                with col_meta:
                    st.download_button(
                        "Tải metadata JSON",
                        data=json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
                        file_name=f"{stem}.json",
                        mime="application/json",
                        key="download_captured_metadata",
                        width="stretch",
                    )
                st.info("Bạn có thể đặt ảnh và JSON này vào thư mục dataset để bổ sung nhãn/kích thước đo chuẩn.")
    else:
        files = st.file_uploader("Ảnh sản phẩm (có thể chọn nhiều ảnh)", type=["png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"],
                                 accept_multiple_files=True, key="flow_images")
        images = [(item.name, item.getvalue()) for item in files]
        st.caption("Một mã sản phẩm, tiêu chuẩn và calibration dùng chung cho lô. Chọn lô khác nếu sản phẩm hoặc thiết lập camera khác nhau.")
    settings = InspectionSettings(board, specification=controls.specification, calibration=calibration,
                                  calibration_error=calibration_error, product_id=product, conditions_confirmed=confirmed,
                                  acquisition_notes=notes, segmentation=method, quality=quality, near_limit_mm=near)
    context = [asdict(board), str(controls.specification), calibration.fingerprint if calibration else None,
               calibration_error, product, confirmed, notes, method, asdict(quality), near, source,
               [(name, sha256(data).hexdigest()) for name, data in images]]
    signature = sha256(json.dumps(context, ensure_ascii=False).encode()).hexdigest()
    too_large = len(images) > 50 or sum(len(data) for _, data in images) > 100_000_000
    if too_large:
        st.error("Mỗi lô tối đa 50 ảnh và tổng 100 MB. Chia nhỏ lô để xử lý.")
    if st.button("Đo, kiểm tra và lưu lịch sử", key="run_full_flow", type="primary",
                 disabled=not images or too_large or bool(st.session_state.flow_pending), width="stretch"):
        outcomes = []
        progress = st.progress(0, text="Đang xử lý ảnh…")
        with st.spinner("Đang hiệu chỉnh, đo và kiểm tra từng ảnh…"):
            for index, outcome in enumerate(inspect_batch(images, settings, source=source.lower())):
                outcomes.append(outcome)
                st.session_state.flow_pending.append(outcome)
                _save_pending(store)
                progress.progress((index + 1) / len(images), text=f"Đã xử lý {index + 1}/{len(images)} ảnh")
        st.session_state.flow_latest = (signature, outcomes)
        st.rerun()
    latest = st.session_state.get("flow_latest")
    if latest is not None and latest[0] == signature:
        outcomes = latest[1]
        records = [item.record for item in outcomes]
        unsaved = {item.record["run_id"] for item in st.session_state.flow_pending}
        st.caption(f"Lô vừa xử lý: {len(records)} lượt · đã lưu {sum(r['run_id'] not in unsaved for r in records)} · chưa lưu {sum(r['run_id'] in unsaved for r in records)}")
        render_counts(records)
        st.dataframe(records_table(records), hide_index=True, alt="Kết quả và mã lỗi từng ảnh trong lô vừa xử lý")
        chosen = st.selectbox("Xem lượt trong lô", [r["run_id"] for r in records],
                              format_func=lambda value: next(f"{r['filename']} · {value[:8]}" for r in records if r["run_id"] == value), key="flow_run_detail")
        render_run_detail(next(item for item in outcomes if item.record["run_id"] == chosen), key="flow_detail")
    elif latest is not None:
        st.info("Đầu vào đã thay đổi; cần chạy lượt mới. Kết quả đã lưu có thể xem ở trang Lịch sử.")
