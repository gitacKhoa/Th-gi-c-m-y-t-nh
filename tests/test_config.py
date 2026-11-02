"""Configuration contracts: physical inputs must be explicit and valid."""

import pytest

from visiongauge.config import ChessboardConfig, ConfigurationError, load_config


def test_default_file_and_opencv_axis_order():
    board = load_config().chessboard
    assert board.pattern_size == (9, 6)
    assert board.square_size_mm == 25.0


def test_default_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_config().chessboard.pattern_size == (9, 6)


@pytest.mark.parametrize("axis", ["columns", "rows"])
@pytest.mark.parametrize("value", [0, -1, 2, 3.5, True, "9", None])
def test_reject_invalid_inner_corner_counts(axis, value):
    with pytest.raises(ConfigurationError, match=axis):
        ChessboardConfig(**{axis: value})


@pytest.mark.parametrize("value", [0, -2, float("nan"), float("inf"),
                                  float("-inf"), True, "25", None])
def test_reject_invalid_square_size(value):
    with pytest.raises(ConfigurationError, match="square_size_mm"):
        ChessboardConfig(square_size_mm=value)


def test_load_custom_configuration(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text(
        "[chessboard]\ncolumns = 7\nrows = 5\nsquare_size_mm = 12.5\n",
        encoding="utf-8",
    )
    board = load_config(path).chessboard
    assert board.pattern_size == (7, 5)
    assert board.square_size_mm == 12.5


def test_missing_configuration_is_explicit(tmp_path):
    with pytest.raises(ConfigurationError, match="Không đọc được"):
        load_config(tmp_path / "missing.toml")


@pytest.mark.parametrize("contents", [
    "[broken", "", "chessboard = 42",
    "[chessboard]\ncolumns = 9\nrows = 6\n",
    "[chessboard]\ncolumns = 9\nrows = 6\nsquare_size_mm = -1\n",
    "[chessboard]\ncolumns = 9\nrows = 6\nsquare_size_mm = 25\nextra = 1\n",
    "unexpected = 1\n[chessboard]\ncolumns = 9\nrows = 6\nsquare_size_mm = 25\n",
])
def test_reject_malformed_or_invalid_configuration(tmp_path, contents):
    path = tmp_path / "invalid.toml"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_config(path)
