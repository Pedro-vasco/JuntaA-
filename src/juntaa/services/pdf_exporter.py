from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
import tempfile
from typing import Callable, Iterable

from PIL import Image
from pypdf import PdfReader, PdfWriter

from juntaa.config import COMPRESSION_PRESETS, CompressionPreset
from juntaa.converters.docx_adapter import DocxConversionError, convert_docx_to_pdf
from juntaa.models import MergeItem

LOGGER = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


class ExportError(RuntimeError):
    pass


def export_items_to_pdf(
    items: Iterable[MergeItem],
    destination: Path,
    compression_label: str,
    progress_callback: ProgressCallback | None = None,
) -> list[str]:
    items = list(items)
    if not items:
        raise ExportError("Adicione ao menos um arquivo antes de exportar.")

    try:
        preset = COMPRESSION_PRESETS[compression_label]
    except KeyError as exc:
        raise ExportError("Nível de compressão inválido.") from exc
    writer = PdfWriter()
    warnings: list[str] = []

    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="juntaa-") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        total = len(items)

        for index, item in enumerate(items, start=1):
            _notify(progress_callback, index - 1, total, f"Processando {item.path.name}...")
            try:
                if item.item_type == "pdf":
                    _append_pdf(item.path, writer)
                elif item.item_type == "image":
                    temp_pdf = _convert_image_to_pdf(item.path, tmp_dir, preset, index)
                    _append_pdf(temp_pdf, writer)
                elif item.item_type == "docx":
                    temp_pdf = tmp_dir / f"docx-{index}.pdf"
                    convert_docx_to_pdf(item.path, temp_pdf)
                    _append_pdf(temp_pdf, writer)
                else:
                    raise ExportError(f"Tipo de item não suportado: {item.item_type}")
            except DocxConversionError as exc:
                LOGGER.warning("DOCX ignorado durante exportação: %s", item.path)
                warnings.append(f"{item.path.name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Falha ao processar %s", item.path)
                raise ExportError(f"Falha ao processar '{item.path.name}': {exc}") from exc
            _notify(progress_callback, index, total, f"Concluído: {item.path.name}")

        if not writer.pages:
            raise ExportError(
                "Nenhuma página válida foi gerada. Revise os arquivos adicionados e tente novamente."
            )

        if hasattr(writer, "compress_identical_objects"):
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

        with destination.open("wb") as output_file:
            writer.write(output_file)

    LOGGER.info("PDF exportado com sucesso em %s", destination)
    return warnings


def _append_pdf(pdf_path: Path, writer: PdfWriter) -> None:
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)


def _convert_image_to_pdf(source: Path, tmp_dir: Path, preset: CompressionPreset, index: int) -> Path:
    with Image.open(source) as image:
        image.load()
        normalized = _normalize_image(image, preset)

    pdf_path = tmp_dir / f"image-{index}.pdf"
    jpeg_buffer = BytesIO()
    normalized.save(
        jpeg_buffer,
        format="JPEG",
        quality=preset.jpeg_quality,
        optimize=True,
        dpi=(preset.dpi, preset.dpi),
    )
    jpeg_buffer.seek(0)
    with Image.open(jpeg_buffer) as compressed_image:
        compressed_image.convert("RGB").save(pdf_path, format="PDF", resolution=preset.dpi)
    return pdf_path


def _normalize_image(image: Image.Image, preset: CompressionPreset) -> Image.Image:
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, "white")
        converted = image.convert("RGBA")
        background.paste(converted, mask=converted.getchannel("A") if "A" in converted.getbands() else None)
        image = background
    elif image.mode == "L":
        image = image.convert("RGB")

    normalized = image.copy()
    normalized.thumbnail((preset.max_dimension, preset.max_dimension), Image.Resampling.LANCZOS)
    return normalized


def _notify(callback: ProgressCallback | None, current: int, total: int, message: str) -> None:
    if callback:
        callback(current, total, message)
