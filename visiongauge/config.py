"""Load and validate configuration without performing image processing."""

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.toml"


class ConfigurationError(ValueError):
    """Configuration is missing, unreadable, malformed, or invalid."""


@dataclass(frozen=True)
class ChessboardConfig:
    """Inner corner counts and physical square edge length in millimetres."""

    columns: int = 9
    rows: int = 6
    square_size_mm: float = 25.0

    def __post_init__(self) -> None:
        for name, value in (("columns", self.columns), ("rows", self.rows)):
            if type(value) is not int or value < 3:
                raise ConfigurationError(
                    f"{name}: số góc trong phải là số nguyên >= 3."
                )
        size = self.square_size_mm
        if (
            type(size) not in (int, float)
            or not isfinite(size)
            or size <= 0
        ):
            raise ConfigurationError("square_size_mm phải là số hữu hạn > 0 mm.")

    @property
    def pattern_size(self) -> tuple[int, int]:
        """OpenCV patternSize order is (columns, rows)."""
        return self.columns, self.rows


@dataclass(frozen=True)
class AppConfig:
    chessboard: ChessboardConfig = field(default_factory=ChessboardConfig)


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Read a strict TOML configuration; never silently use invalid values."""
    config_path = Path(path)
    try:
        with config_path.open("rb") as stream:
            payload = tomllib.load(stream)
    except (OSError, ValueError) as exc:
        raise ConfigurationError(
            f"Không đọc được cấu hình {config_path}: {exc}"
        ) from exc

    if set(payload) != {"chessboard"}:
        raise ConfigurationError("Cấu hình phải có đúng bảng [chessboard].")
    board = payload["chessboard"]
    expected = {"columns", "rows", "square_size_mm"}
    if not isinstance(board, dict) or set(board) != expected:
        raise ConfigurationError(
            "[chessboard] phải có đúng columns, rows và square_size_mm."
        )
    return AppConfig(chessboard=ChessboardConfig(**board))
