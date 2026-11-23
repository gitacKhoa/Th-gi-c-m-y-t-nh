"""Fail-closed product inspection, independent of OpenCV and Streamlit."""

from .models import (
    Number, ProductTolerance, ProductInspection, DimensionInspection, InspectionStatus,
    as_decimal, exact_sum,
)
from .rules import DecisionRule, InclusiveLimitsRule


def evaluate_tolerance(
    length_mm: Number | None, width_mm: Number | None, specification: ProductTolerance, *,
    measurement_succeeded: bool, failure_reason: str | None = None,
    rule: DecisionRule | None = None,
    length_uncertainty_mm: Number | None = None, width_uncertainty_mm: Number | None = None,
) -> ProductInspection:
    """Invalid/failed measurements are NOT_EVALUABLE, never PASS or product FAIL.

    Signed deviations define limits: nominal + lower/upper deviation.
    Valid specifications are required; invalid specifications raise ValueError.
    Uncertainty values, when supplied, must be expanded uncertainties in mm;
    the default policy refuses them instead of silently ignoring them.
    """
    if not isinstance(specification, ProductTolerance):
        raise ValueError("Cấu hình dung sai sản phẩm không hợp lệ.")
    policy = rule if rule is not None else InclusiveLimitsRule()
    specs = (("length", specification.length), ("width", specification.width))

    def unavailable(reason: str) -> ProductInspection:
        dimensions = tuple(DimensionInspection(name, spec, None, None, InspectionStatus.NOT_EVALUABLE, reason)
                           for name, spec in specs)
        return ProductInspection(InspectionStatus.NOT_EVALUABLE, dimensions, policy.rule_id, reason)

    if measurement_succeeded is not True or failure_reason:
        return unavailable(failure_reason or "Chưa có phép đo thành công cho ảnh hiện tại.")
    try:
        measured = (as_decimal(length_mm, "length_mm"), as_decimal(width_mm, "width_mm"))
        if min(measured) <= 0 or measured[0] < measured[1]:
            raise ValueError("Số đo phải > 0 và chiều dài >= chiều rộng.")
        uncertainties = tuple(None if value is None else as_decimal(value, "uncertainty_mm")
                              for value in (length_uncertainty_mm, width_uncertainty_mm))
        if any(value is not None and value < 0 for value in uncertainties):
            raise ValueError("Độ không đảm bảo đo phải >= 0 mm.")
    except ValueError as exc:
        return unavailable(str(exc))

    dimensions = []
    for (name, spec), value, uncertainty in zip(specs, measured, uncertainties):
        decision = policy.decide(value, spec, expanded_uncertainty_mm=uncertainty)
        if not isinstance(decision.status, InspectionStatus):
            raise ValueError("Quy tắc quyết định trả về trạng thái không được hỗ trợ.")
        dimensions.append(DimensionInspection(name, spec, value, exact_sum(value, spec.nominal_mm.copy_negate()),
                                              decision.status, decision.reason))
    if any(item.status == InspectionStatus.NOT_EVALUABLE for item in dimensions):
        status, reason = InspectionStatus.NOT_EVALUABLE, "Có kích thước chưa đủ điều kiện đánh giá."
    elif any(item.status == InspectionStatus.FAIL for item in dimensions):
        status, reason = InspectionStatus.FAIL, "Có kích thước nằm ngoài giới hạn cho phép."
    else:
        status, reason = InspectionStatus.PASS, "Cả chiều dài và chiều rộng nằm trong giới hạn cho phép."
    return ProductInspection(status, tuple(dimensions), policy.rule_id, reason)
