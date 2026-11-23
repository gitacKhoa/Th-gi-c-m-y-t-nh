"""Tolerance specifications and immutable three-state inspection results, in mm."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import Enum
from math import isfinite
from numbers import Real


Number = int | float | Decimal


def as_decimal(value: Number, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError(f"{name}: cần một số hữu hạn, không phải chuỗi/bool/giá trị trống.")
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not isfinite(float(result)):
            raise ValueError(f"{name}: cần một số hữu hạn trong miền tính toán.")
    except (OverflowError, ArithmeticError) as exc:
        raise ValueError(f"{name}: số không hợp lệ.") from exc
    return result


def exact_sum(left: Decimal, right: Decimal) -> Decimal:
    """Avoid float boundary artefacts and caller-dependent Decimal precision."""
    with localcontext() as context:
        context.prec = max(28, max(left.adjusted(), right.adjusted(), 0)
                           - min(left.as_tuple().exponent, right.as_tuple().exponent, 0) + 3)
        return left + right


@dataclass(frozen=True, init=False)
class DimensionTolerance:
    nominal_mm: Decimal
    lower_deviation_mm: Decimal
    upper_deviation_mm: Decimal

    def __init__(self, nominal_mm: Number, lower_deviation_mm: Number, upper_deviation_mm: Number):
        for name, value in (("nominal_mm", nominal_mm), ("lower_deviation_mm", lower_deviation_mm),
                            ("upper_deviation_mm", upper_deviation_mm)):
            object.__setattr__(self, name, as_decimal(value, name))
        if self.nominal_mm <= 0:
            raise ValueError("Kích thước danh nghĩa phải > 0 mm.")
        if self.lower_deviation_mm > self.upper_deviation_mm:
            raise ValueError("Sai lệch dưới phải <= sai lệch trên.")
        if self.lower_limit_mm <= 0:
            raise ValueError("Giới hạn dưới phải > 0 mm.")
        as_decimal(self.upper_limit_mm, "upper_limit_mm")

    @property
    def lower_limit_mm(self) -> Decimal:
        return exact_sum(self.nominal_mm, self.lower_deviation_mm)

    @property
    def upper_limit_mm(self) -> Decimal:
        return exact_sum(self.nominal_mm, self.upper_deviation_mm)


@dataclass(frozen=True)
class ProductTolerance:
    length: DimensionTolerance
    width: DimensionTolerance

    def __post_init__(self):
        if not isinstance(self.length, DimensionTolerance) or not isinstance(self.width, DimensionTolerance):
            raise ValueError("Cần dung sai hợp lệ cho cả chiều dài và chiều rộng.")
        if self.length.nominal_mm < self.width.nominal_mm:
            raise ValueError("Chiều dài danh nghĩa phải >= chiều rộng danh nghĩa.")


class InspectionStatus(str, Enum):
    PASS = "ĐẠT"
    FAIL = "KHÔNG ĐẠT"
    NOT_EVALUABLE = "KHÔNG THỂ ĐÁNH GIÁ"


@dataclass(frozen=True)
class RuleDecision:
    status: InspectionStatus
    reason: str


@dataclass(frozen=True)
class DimensionInspection:
    name: str
    specification: DimensionTolerance
    measured_mm: Decimal | None
    deviation_mm: Decimal | None
    status: InspectionStatus
    reason: str


@dataclass(frozen=True)
class ProductInspection:
    status: InspectionStatus
    dimensions: tuple[DimensionInspection, DimensionInspection]
    rule_id: str
    reason: str
