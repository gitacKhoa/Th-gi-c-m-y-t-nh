"""Tolerance controls and live inspection of the current measurement only."""

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
import streamlit as st

from visiongauge.tolerance import DimensionTolerance, ProductTolerance, InspectionStatus, evaluate_tolerance
from .workflow import MeasurementWorkflow


@dataclass(frozen=True)
class ToleranceControls:
    enabled: bool
    specification: ProductTolerance | None = None
    error: str | None = None


def render_tolerance_controls(*, required: bool = False) -> ToleranceControls:
    st.divider()
    enabled = required or st.toggle("Kiểm tra dung sai", key="tolerance_enabled", persist_state="session")
    if required:
        st.subheader("Tiêu chuẩn và dung sai")
    if not enabled:
        return ToleranceControls(False)
    st.caption("Nhập sai lệch có dấu: ví dụ −0,5 / +1 mm. Giới hạn = danh nghĩa + sai lệch; hai biên được tính là ĐẠT.")
    values = []
    for key, label in (("length", "Chiều dài"), ("width", "Chiều rộng")):
        with st.expander(f"Dung sai {label.lower()}", expanded=True):
            nominal = st.number_input(
                f"{label} danh nghĩa (mm)", value=None, min_value=0.0, step=0.1, format="%.6f",
                key=f"tolerance_{key}_nominal", persist_state="session", placeholder="Nhập kích thước tiêu chuẩn",
            )
            lower = st.number_input(
                f"Sai lệch dưới — {label.lower()} (mm)", value=None, step=0.1, format="%.6f",
                key=f"tolerance_{key}_lower", persist_state="session", placeholder="Nhập sai lệch có dấu",
            )
            upper = st.number_input(
                f"Sai lệch trên — {label.lower()} (mm)", value=None, step=0.1, format="%.6f",
                key=f"tolerance_{key}_upper", persist_state="session", placeholder="Nhập sai lệch có dấu",
            )
            values.append((nominal, lower, upper))
    if any(value is None for dimension in values for value in dimension):
        return ToleranceControls(True, error="Nhập đầy đủ danh nghĩa, sai lệch dưới và trên cho cả hai kích thước.")
    try:
        specification = ProductTolerance(*(DimensionTolerance(*dimension) for dimension in values))
    except ValueError as exc:
        return ToleranceControls(True, error=f"Cấu hình dung sai không hợp lệ: {exc}")
    for label, spec in (("Chiều dài", specification.length), ("Chiều rộng", specification.width)):
        st.caption(f"{label}: [{spec.lower_limit_mm}, {spec.upper_limit_mm}] mm")
    return ToleranceControls(True, specification)


def _number(value: Decimal | None, *, signed: bool = False) -> str:
    if value is None:
        return "—"
    # Keep all supplied digits: rounding must not conceal a just-outside result.
    return format(value, "+f" if signed else "f")


def render_tolerance_result(workflow: MeasurementWorkflow, controls: ToleranceControls) -> None:
    if not controls.enabled:
        return
    with st.container(border=True):
        st.subheader("Kiểm tra dung sai sản phẩm")
        if controls.error or controls.specification is None:
            st.warning(f"KHÔNG THỂ ĐÁNH GIÁ: {controls.error or 'Chưa có cấu hình dung sai.'}")
            return
        failure = workflow.input_error or workflow.board_error or workflow.measurement_error
        result = workflow.result
        inspection = evaluate_tolerance(
            result.length_mm if result is not None else None,
            result.width_mm if result is not None else None,
            controls.specification, measurement_succeeded=result is not None and not failure,
            failure_reason=failure,
        )
        alert = {InspectionStatus.PASS: st.success, InspectionStatus.FAIL: st.error,
                 InspectionStatus.NOT_EVALUABLE: st.warning}[inspection.status]
        alert(f"{inspection.status.value}: {inspection.reason}")
        rows = []
        for item in inspection.dimensions:
            label = "Chiều dài" if item.name == "length" else "Chiều rộng"
            rows.append({"Kích thước": label, "Danh nghĩa (mm)": _number(item.specification.nominal_mm),
                         "Giới hạn dưới (mm)": _number(item.specification.lower_limit_mm),
                         "Giới hạn trên (mm)": _number(item.specification.upper_limit_mm),
                         "Đo được (mm)": _number(item.measured_mm),
                         "Độ lệch (mm)": _number(item.deviation_mm, signed=True),
                         "Kết luận": item.status.value, "Chi tiết": item.reason})
            if item.status == InspectionStatus.FAIL:
                st.error(f"{label}: {item.reason} Độ lệch so với danh nghĩa {_number(item.deviation_mm, signed=True)} mm.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, key="tolerance_results",
                     alt="Giới hạn, số đo, độ lệch và trạng thái dung sai từng kích thước")
        st.caption(
            "Quy tắc: so sánh trực tiếp với hai giới hạn, chưa xét độ không đảm bảo đo. "
            "Dùng số đo chưa làm tròn; số chữ số hiển thị không chứng nhận độ chính xác. "
            "Ảnh PNG tải xuống chỉ chứa phép đo hình học, không chứa kết luận dung sai."
        )
