"""Session-owned calibration photos, independent of Streamlit widget lifetime."""

from dataclasses import dataclass, field
from io import BytesIO
from zipfile import ZipFile, ZIP_STORED

from visiongauge.errors import VisionGaugeError
from visiongauge.image_io import decode_image


@dataclass
class CalibrationCaptures:
    images: list[tuple[str, bytes]] = field(default_factory=list)
    image_size: tuple[int, int] | None = None
    sequence: int = 0
    widget_generation: int = 0
    resolution: str = "720p"

    def add(self, data: bytes) -> str:
        """Keep original JPEG bytes; never resize a frame to fit earlier captures."""
        image = decode_image(data)
        size = (image.shape[1], image.shape[0])
        if self.image_size is not None and size != self.image_size:
            raise VisionGaugeError(
                f"Ảnh mới {size[0]} × {size[1]} khác bộ ảnh đang chụp "
                f"{self.image_size[0]} × {self.image_size[1]}. "
                "Giữ nguyên camera/chế độ chụp hoặc xóa bộ ảnh để bắt đầu lại."
            )
        if any(payload == data for _, payload in self.images):
            raise VisionGaugeError("Ảnh này đã được thêm. Hãy thay đổi vị trí/góc nghiêng bàn cờ và chụp ảnh mới.")
        self.sequence += 1
        name = f"camera_{self.sequence:03d}.jpg"
        self.images.append((name, bytes(data)))
        self.image_size = size
        self.widget_generation += 1
        return name

    def remove(self, name: str) -> None:
        self.images = [(key, data) for key, data in self.images if key != name]
        if not self.images:
            self.image_size = None

    def clear(self) -> None:
        self.images.clear()
        self.image_size = None
        self.widget_generation += 1

    def archive(self) -> bytes:
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_STORED) as archive:
            for name, data in self.images:
                archive.writestr(name, data)
        return output.getvalue()
