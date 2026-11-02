"""Expected failures that callers can present as KHÔNG THỂ ĐÁNH GIÁ."""


class VisionGaugeError(ValueError):
    """Base class for recoverable input and measurement failures."""


class InvalidImageError(VisionGaugeError):
    """Image cannot be decoded or is not a supported uint8 image."""


class CalibrationRequiredError(VisionGaugeError):
    """Lens distortion has not been addressed by the caller."""


class CameraCalibrationError(VisionGaugeError):
    """Camera data, fit, saved model, or image resolution is invalid."""


class ChessboardNotFoundError(VisionGaugeError):
    """The complete configured inner-corner grid was not found."""


class UnreliableMappingError(VisionGaugeError):
    """Planar correspondence fails geometric or reprojection checks."""


class ProductNotFoundError(VisionGaugeError):
    """No separate, complete rectangular contour passes the checks."""


class AmbiguousProductError(VisionGaugeError):
    """More than one plausible product is present."""


class UnreliableMeasurementError(VisionGaugeError):
    """The product geometry or mapping is outside supported conditions."""
