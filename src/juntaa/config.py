from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

APP_NAME = "JuntaA"
OUTPUT_FORMATS = ("PDF",)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | DOCX_EXTENSIONS


@dataclass(frozen=True)
class CompressionPreset:
    label: str
    dpi: int
    jpeg_quality: int
    max_dimension: int
    optimize_jpeg: bool


COMPRESSION_PRESETS = {
    "Baixa": CompressionPreset(label="Baixa", dpi=300, jpeg_quality=92, max_dimension=2600, optimize_jpeg=False),
    "Média": CompressionPreset(label="Média", dpi=200, jpeg_quality=80, max_dimension=1800, optimize_jpeg=True),
    "Alta": CompressionPreset(label="Alta", dpi=120, jpeg_quality=65, max_dimension=1280, optimize_jpeg=True),
}


def get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_log_file() -> Path:
    log_dir = get_runtime_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "app.log"
