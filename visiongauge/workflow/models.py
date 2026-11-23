"""Inputs and immutable payloads for a traceable, calibrated inspection run."""

from dataclasses import dataclass, field

from visiongauge.calibration import CameraCalibration
from visiongauge.config import ChessboardConfig
from visiongauge.tolerance import ProductTolerance
from .quality import QualityOptions


@dataclass(frozen=True)
class InspectionSettings:
    board: ChessboardConfig
    specification: ProductTolerance | None = None
    calibration: CameraCalibration | None = None
    calibration_error: str | None = None
    product_id: str = ""
    conditions_confirmed: bool = False
    acquisition_notes: str = ""
    segmentation: str = "threshold"
    quality: QualityOptions = field(default_factory=QualityOptions)
    near_limit_mm: float = 0.2


@dataclass(frozen=True)
class RunOutcome:
    """A completed attempt; bytes and metadata are saved in one DB transaction.

    The record is a JSON snapshot, not a live reference to UI settings. Repeated
    persistence of the same run_id is idempotent; a new measurement gets a new ID.
    """

    record: dict
    source_bytes: bytes
    annotated_png: bytes | None = None


NOT_EVALUABLE = "KHÔNG THỂ ĐÁNH GIÁ"
PASS = "ĐẠT"
FAIL = "KHÔNG ĐẠT"
