"""Tolerance boundary and invalid-input contracts, independent of image processing."""

from decimal import Decimal, localcontext

import numpy as np
import pytest

from visiongauge.tolerance import (
    DimensionTolerance, ProductTolerance, InspectionStatus as Status, RuleDecision,
    evaluate_tolerance,
)


def specification():
    return ProductTolerance(DimensionTolerance(160, -2, 3), DimensionTolerance(80, -1, 1.5))


def test_asymmetric_signed_limits_and_deviations():
    spec = specification()
    assert spec.length.lower_limit_mm == 158 and spec.length.upper_limit_mm == 163
    assert spec.width.lower_limit_mm == 79 and spec.width.upper_limit_mm == Decimal("81.5")
    result = evaluate_tolerance(159, 81, spec, measurement_succeeded=True)
    assert result.status == Status.PASS
    assert [dimension.deviation_mm for dimension in result.dimensions] == [-1, 1]
    assert result.rule_id == "inclusive_limits_v1"


@pytest.mark.parametrize("length,width", [(158, 79), (158, 81.5), (163, 79), (163, 81.5), (160, 80)])
def test_exact_limits_are_inclusive(length, width):
    result = evaluate_tolerance(length, width, specification(), measurement_succeeded=True)
    assert result.status == Status.PASS
    assert all(dimension.status == Status.PASS for dimension in result.dimensions)


@pytest.mark.parametrize("length,width,failed,reason", [
    (157.999999, 80, "length", "Dưới"), (163.000001, 80, "length", "Trên"),
    (160, 78.999999, "width", "Dưới"), (160, 81.500001, "width", "Trên"),
])
def test_just_outside_is_not_rounded_into_acceptance(length, width, failed, reason):
    result = evaluate_tolerance(length, width, specification(), measurement_succeeded=True)
    assert result.status == Status.FAIL
    dimensions = {dimension.name: dimension for dimension in result.dimensions}
    assert dimensions[failed].status == Status.FAIL
    assert reason in dimensions[failed].reason
    assert sum(dimension.status == Status.PASS for dimension in result.dimensions) == 1


def test_both_dimensions_fail_and_zero_tolerance():
    result = evaluate_tolerance(165, 78, specification(), measurement_succeeded=True)
    assert all(dimension.status == Status.FAIL for dimension in result.dimensions)
    exact = ProductTolerance(DimensionTolerance(160, 0, 0), DimensionTolerance(80, 0, 0))
    assert evaluate_tolerance(160, 80, exact, measurement_succeeded=True).status == Status.PASS
    assert evaluate_tolerance(160, np.nextafter(80., 81.), exact, measurement_succeeded=True).status == Status.FAIL


def test_decimal_limits_without_binary_float_or_context_widening():
    spec = ProductTolerance(DimensionTolerance(.1, 0, .2), DimensionTolerance(.05, 0, 0))
    assert spec.length.upper_limit_mm == Decimal("0.3")
    assert evaluate_tolerance(.3, .05, spec, measurement_succeeded=True).status == Status.PASS
    assert evaluate_tolerance(np.nextafter(.3, 1), .05, spec, measurement_succeeded=True).status == Status.FAIL
    with localcontext() as context:
        context.prec = 3
        larger = DimensionTolerance(160.123456, -.000001, .000001)
        assert larger.lower_limit_mm == Decimal("160.123455")
        assert larger.upper_limit_mm == Decimal("160.123457")


@pytest.mark.parametrize("lower,upper,inside,outside", [(.2, .5, 160.3, 160), (-.5, -.2, 159.7, 160), (0, .5, 160, 159.9)])
def test_same_sign_and_one_sided_tolerances(lower, upper, inside, outside):
    spec = ProductTolerance(DimensionTolerance(160, lower, upper), DimensionTolerance(80, 0, 0))
    assert evaluate_tolerance(inside, 80, spec, measurement_succeeded=True).status == Status.PASS
    assert evaluate_tolerance(outside, 80, spec, measurement_succeeded=True).status == Status.FAIL


@pytest.mark.parametrize("values", [
    (0, -1, 1), (-1, 0, 0), (160, 2, 1), (160, -160, 1), (160, -161, 0),
    (None, 0, 0), ("160", 0, 0), (True, 0, 0), (160, False, 1), (160, 0, "1"),
    (float("nan"), 0, 0), (float("inf"), 0, 0), (160, float("-inf"), 1),
    (160, 0, float("nan")), (Decimal("sNaN"), 0, 1), (1e308, 0, 1e308),
])
def test_invalid_specifications_raise(values):
    with pytest.raises(ValueError):
        DimensionTolerance(*values)


def test_invalid_product_specifications_raise():
    with pytest.raises(ValueError):
        ProductTolerance(DimensionTolerance(80, 0, 0), DimensionTolerance(160, 0, 0))
    with pytest.raises(ValueError):
        ProductTolerance(None, None)
    with pytest.raises(ValueError):
        evaluate_tolerance(160, 80, None, measurement_succeeded=True)


@pytest.mark.parametrize("length,width", [
    (None, 80), (160, None), (float("nan"), 80), (160, float("inf")), (0, 80), (-1, 80),
    (160, 0), (160, -80), (80, 160), (True, 80), (160, False), ("160", 80), (160, "80"),
])
def test_invalid_measurement_never_passes_or_marks_product_failed(length, width):
    result = evaluate_tolerance(length, width, specification(), measurement_succeeded=True)
    assert result.status == Status.NOT_EVALUABLE
    assert all(item.status == Status.NOT_EVALUABLE and item.measured_mm is None for item in result.dimensions)


@pytest.mark.parametrize("success,reason", [(False, None), (False, "Không tìm thấy sản phẩm"), (True, "Ảnh không đáng tin cậy"), (None, None), (1, None)])
def test_failure_flag_or_reason_overrides_even_valid_old_dimensions(success, reason):
    result = evaluate_tolerance(160, 80, specification(), measurement_succeeded=success, failure_reason=reason)
    assert result.status == Status.NOT_EVALUABLE
    assert all(item.deviation_mm is None for item in result.dimensions)


@pytest.mark.parametrize("uncertainty", [-1, float("nan"), float("inf"), True, "0.1", 0, .1])
def test_invalid_or_unsupported_uncertainty_is_not_silently_ignored(uncertainty):
    result = evaluate_tolerance(160, 80, specification(), measurement_succeeded=True, length_uncertainty_mm=uncertainty)
    assert result.status == Status.NOT_EVALUABLE


def test_decision_rule_extension_receives_validated_values_and_can_defer():
    class RecordingRule:
        rule_id = "test_only_policy"

        def __init__(self):
            self.calls = []

        def decide(self, measured_mm, specification, *, expanded_uncertainty_mm=None):
            self.calls.append((measured_mm, specification, expanded_uncertainty_mm))
            return RuleDecision(Status.NOT_EVALUABLE, "Test extension; no uncertainty rule implemented.")

    rule = RecordingRule()
    result = evaluate_tolerance(160, 80, specification(), measurement_succeeded=True, rule=rule,
                                length_uncertainty_mm=.2, width_uncertainty_mm=.1)
    assert result.status == Status.NOT_EVALUABLE and result.rule_id == rule.rule_id
    assert [call[0] for call in rule.calls] == [Decimal(160), Decimal(80)]
    assert [call[2] for call in rule.calls] == [Decimal(".2"), Decimal(".1")]
    rule.calls.clear()
    evaluate_tolerance(160, 80, specification(), measurement_succeeded=False, rule=rule)
    assert not rule.calls  # Failure cannot be overridden by a custom policy.
