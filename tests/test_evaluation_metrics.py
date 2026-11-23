"""Hand-calculated formula checks; these numbers are test vectors, not experiments."""

import numpy as np
import pandas as pd
import pytest

from visiongauge.evaluation.metrics import measurement_errors, error_statistics
from visiongauge.evaluation.summary import summarize_results


def test_signed_absolute_and_relative_errors():
    errors = measurement_errors([100, 200, 50], [103, 196, 50])
    np.testing.assert_array_equal(errors["signed_error_mm"], [3, -4, 0])
    np.testing.assert_array_equal(errors["absolute_error_mm"], [3, 4, 0])
    np.testing.assert_allclose(errors["relative_error_pct"], [3, 2, 0])


def test_mae_rmse_bias_max_and_mape_do_not_cancel_signed_errors():
    stats = error_statistics([100, 200, 50], [103, 196, 50])
    assert stats == pytest.approx({"n": 3, "mean_error_mm": -1 / 3, "mae_mm": 7 / 3,
                                 "rmse_mm": np.sqrt(25 / 3), "max_absolute_error_mm": 4, "mape_pct": 5 / 3})


def test_exact_measurements_have_zero_errors():
    stats = error_statistics([160, 80], [160, 80])
    assert stats["n"] == 2
    assert all(value == 0 for key, value in stats.items() if key != "n")


def test_single_sample_and_empty_samples():
    assert error_statistics([80], [78]) == pytest.approx({"n": 1, "mean_error_mm": -2, "mae_mm": 2,
                                                        "rmse_mm": 2, "max_absolute_error_mm": 2, "mape_pct": 2.5})
    stats = error_statistics([], [])
    assert stats["n"] == 0
    assert all(np.isnan(value) for key, value in stats.items() if key != "n")


@pytest.mark.parametrize("reference,measured", [
    ([0], [1]), ([-1], [1]), ([1], [0]), ([1], [-1]), ([np.nan], [1]), ([1], [np.inf]),
    ([np.inf], [1]), ([1], [np.nan]), ([1, 2], [1]), ([[1]], [[1]]),
    ([True], [1]), (["1"], [1]), ([1], ["1"]), (1, 1), ([1e-300], [1e300]),
])
def test_invalid_statistics_input_is_not_silently_dropped(reference, measured):
    with pytest.raises(ValueError):
        error_statistics(reference, measured)


def test_large_finite_rmse_does_not_overflow_when_squared():
    assert error_statistics([1e200], [2e200])["rmse_mm"] == pytest.approx(1e200)


def summary_fixture():
    # Two products plus an all-failed product, with unequal group sizes.
    return pd.DataFrame([
        ["A", "bright", "success", 100, 50, 103, 49],
        ["A", "dim", "success", 100, 50, 99, 52],
        ["B", "bright", "success", 200, 100, 204, 100],
        ["B", "bright", "failed", 200, 100, np.nan, np.nan],
        ["C", "dim", "failed", 160, 80, np.nan, np.nan],
    ], columns=["product_id", "condition_id", "status", "reference_length_mm", "reference_width_mm",
                "measured_length_mm", "measured_width_mm"])


def test_overall_uses_per_image_errors_and_counts_failures():
    summary = summarize_results(summary_fixture()).set_index("dimension")
    length, width = summary.loc["length"], summary.loc["width"]
    assert length.total_images == 5 and length.success_images == 3 and length.failed_images == 2
    assert length.success_rate_pct == 60 and length.n == 3
    assert length.mae_mm == pytest.approx(8 / 3)
    assert length.rmse_mm == pytest.approx(np.sqrt(26 / 3))
    assert length.mean_error_mm == 2
    assert length.mape_pct == pytest.approx(2)
    assert width.mae_mm == 1 and width.rmse_mm == pytest.approx(np.sqrt(5 / 3))
    assert width.mean_error_mm == pytest.approx(1 / 3)
    assert width.mape_pct == 2


def test_product_condition_and_joint_summaries():
    table = summary_fixture()
    product = summarize_results(table, ("product_id",)).set_index(["product_id", "dimension"])
    assert product.loc[("A", "length"), "mae_mm"] == 2
    assert product.loc[("A", "length"), "rmse_mm"] == pytest.approx(np.sqrt(5))
    assert product.loc[("C", "length"), "n"] == 0
    assert np.isnan(product.loc[("C", "length"), "mae_mm"])
    condition = summarize_results(table, ("condition_id",)).set_index(["condition_id", "dimension"])
    assert condition.loc[("bright", "length"), "mae_mm"] == 3.5
    assert condition.loc[("bright", "length"), "rmse_mm"] == pytest.approx(np.sqrt(12.5))
    assert condition.loc[("bright", "length"), "success_rate_pct"] == pytest.approx(200 / 3)
    joint = summarize_results(table, ("product_id", "condition_id"))
    assert len(joint) == 8
    assert joint.total_images.sum() == 10  # Each image counted once per dimension.


def test_empty_summary_and_invalid_success_row():
    table = summary_fixture().iloc[:0]
    summary = summarize_results(table)
    assert summary.n.tolist() == [0, 0]
    assert summary.success_rate_pct.isna().all()
    assert summarize_results(table, ("product_id",)).empty
    broken = summary_fixture()
    broken.loc[0, "measured_width_mm"] = np.nan
    with pytest.raises(ValueError):
        summarize_results(broken)
    with pytest.raises(ValueError):
        summarize_results(pd.DataFrame())
