"""User-configured inspection of real pipeline results and stale-result prevention."""

from dataclasses import replace

import pytest

from tests.test_app import start_app, configure_board, upload, measured_app


def configure_tolerance(app, length=65., width=35., lower=-1., upper=1.):
    app.toggle(key="tolerance_enabled").set_value(True).run()
    for name, nominal in (("length", length), ("width", width)):
        app.number_input(key=f"tolerance_{name}_nominal").set_value(nominal)
        app.number_input(key=f"tolerance_{name}_lower").set_value(lower)
        app.number_input(key=f"tolerance_{name}_upper").set_value(upper)
    return app.run()


def tolerance_tables(app):
    # Non-selectable dataframes do not expose their key in this AppTest version.
    return [item.value for item in app.dataframe if "Kết luận" in item.value.columns]


def table(app):
    tables = tolerance_tables(app)
    assert len(tables) == 1
    return tables[0]


def test_opt_in_requires_explicit_specification_and_successful_measurement():
    app = start_app()
    assert not app.toggle(key="tolerance_enabled").value
    app.toggle(key="tolerance_enabled").set_value(True).run()
    assert app.number_input(key="tolerance_length_nominal").value is None
    assert any("KHÔNG THỂ ĐÁNH GIÁ" in item.value for item in app.warning)
    configure_tolerance(app)
    assert not app.exception
    assert table(app)["Kết luận"].tolist() == ["KHÔNG THỂ ĐÁNH GIÁ"] * 2
    assert table(app)["Đo được (mm)"].tolist() == ["—"] * 2


def test_measure_then_change_tolerance_reclassifies_without_remeasuring():
    app = configure_tolerance(measured_app())
    assert not app.exception
    assert table(app)["Kết luận"].tolist() == ["ĐẠT", "ĐẠT"]
    original = app.session_state["measurement_workflow"].result
    assert float(table(app)["Độ lệch (mm)"].iloc[0]) == pytest.approx(original.length_mm - 65)
    app.number_input(key="tolerance_length_upper").set_value(0.).run()
    assert app.session_state["measurement_workflow"].result is original
    assert table(app)["Kết luận"].tolist() == ["KHÔNG ĐẠT", "ĐẠT"]
    assert any("Chiều dài:" in item.value and "Trên giới hạn" in item.value for item in app.error)
    app.number_input(key="tolerance_length_upper").set_value(1.).run()
    assert table(app)["Kết luận"].tolist() == ["ĐẠT", "ĐẠT"]


def test_invalid_configuration_removes_previous_pass_without_losing_measurement():
    app = configure_tolerance(measured_app())
    original = app.session_state["measurement_workflow"].result
    app.number_input(key="tolerance_width_lower").set_value(2.).run()
    assert not app.exception
    assert any("KHÔNG THỂ ĐÁNH GIÁ" in item.value for item in app.warning)
    assert not tolerance_tables(app)
    assert app.session_state["measurement_workflow"].result is original
    app.number_input(key="tolerance_width_lower").set_value(-1.).run()
    app.number_input(key="tolerance_width_nominal").set_value(None).run()
    assert any("Nhập đầy đủ" in item.value for item in app.warning)
    assert not tolerance_tables(app)


@pytest.mark.parametrize("change", ["image", "remove", "source", "board", "geometry", "segmentation", "detect_again"])
def test_input_changes_remove_old_classification(change):
    app = configure_tolerance(measured_app())
    if change == "image":
        upload(app, angle=57)
    elif change == "remove":
        app.file_uploader(key="uploaded_image").clear().run()
    elif change == "source":
        app.radio(key="image_source").set_value("Chụp camera").run()
    elif change == "board":
        app.number_input(key="board_columns").set_value(8).run()
    elif change == "geometry":
        app.selectbox(key="image_geometry").set_value("Chưa xác nhận").run()
    elif change == "segmentation":
        app.selectbox(key="segmentation").set_value("Canny").run()
    else:
        app.button(key="detect_board").click().run()
    assert not app.exception
    assert table(app)["Kết luận"].tolist() == ["KHÔNG THỂ ĐÁNH GIÁ"] * 2


@pytest.mark.parametrize("options", [{"include_board": False}, {"include_product": False}])
def test_failed_measurement_is_not_a_tolerance_fail_or_pass(options):
    app = configure_tolerance(upload(configure_board(start_app()), **options))
    app.button(key="start_measurement").click().run()
    assert not app.exception
    assert any("KHÔNG THỂ ĐÁNH GIÁ" in item.value for item in app.warning)
    assert table(app)["Kết luận"].tolist() == ["KHÔNG THỂ ĐÁNH GIÁ"] * 2


def test_nominal_limits_are_preserved_when_switching_pages_and_disabling():
    app = configure_tolerance(measured_app())
    app.toggle(key="tolerance_enabled").set_value(False).run()
    assert not tolerance_tables(app)
    app.toggle(key="tolerance_enabled").set_value(True).run()
    assert app.number_input(key="tolerance_length_nominal").value == 65
    app.radio(key="app_page").set_value("Camera Calibration").run()
    app.radio(key="app_page").set_value("Đo kích thước").run()
    assert not app.exception
    assert app.toggle(key="tolerance_enabled").value
    assert app.number_input(key="tolerance_width_lower").value == -1
    assert table(app)["Kết luận"].tolist() == ["KHÔNG THỂ ĐÁNH GIÁ"] * 2


def test_ui_uses_unrounded_measurement_and_reports_invalid_numeric_result():
    app = configure_tolerance(measured_app())
    workflow = app.session_state["measurement_workflow"]
    result = workflow.result
    workflow.result = replace(result, rectangle=replace(result.rectangle, length_mm=66.00000001))
    app.run()
    assert table(app)["Kết luận"].iloc[0] == "KHÔNG ĐẠT"
    assert table(app)["Đo được (mm)"].iloc[0] == "66.00000001"
    workflow.result = replace(result, rectangle=replace(result.rectangle, length_mm=float("nan")))
    app.run()
    assert not app.exception
    assert table(app)["Kết luận"].tolist() == ["KHÔNG THỂ ĐÁNH GIÁ"] * 2
