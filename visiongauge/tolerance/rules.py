"""Replaceable decision policy; no measurement-uncertainty rule is assumed."""

from decimal import Decimal
from typing import Protocol

from .models import DimensionTolerance, InspectionStatus, RuleDecision


class DecisionRule(Protocol):
    rule_id: str

    def decide(
        self, measured_mm: Decimal, specification: DimensionTolerance, *,
        expanded_uncertainty_mm: Decimal | None = None,
    ) -> RuleDecision: ...


class InclusiveLimitsRule:
    """Compare unrounded values to inclusive limits, without guard bands."""

    rule_id = "inclusive_limits_v1"

    def decide(
        self, measured_mm: Decimal, specification: DimensionTolerance, *,
        expanded_uncertainty_mm: Decimal | None = None,
    ) -> RuleDecision:
        if expanded_uncertainty_mm is not None:
            return RuleDecision(InspectionStatus.NOT_EVALUABLE,
                                "Quy tắc hiện tại chưa hỗ trợ độ không đảm bảo đo; cần quy tắc quyết định phù hợp.")
        if measured_mm < specification.lower_limit_mm:
            return RuleDecision(InspectionStatus.FAIL, "Dưới giới hạn cho phép.")
        if measured_mm > specification.upper_limit_mm:
            return RuleDecision(InspectionStatus.FAIL, "Trên giới hạn cho phép.")
        return RuleDecision(InspectionStatus.PASS, "Trong giới hạn cho phép (bao gồm hai biên).")
