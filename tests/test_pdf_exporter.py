from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader, PdfWriter

from juntaa.converters.docx_adapter import DocxConversionError
from juntaa.models import MergeItem
from juntaa.services.pdf_exporter import ExportError, export_items_to_pdf


class PdfExporterTests(unittest.TestCase):
    def test_export_combines_pdf_and_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / "sample.png"
            pdf_path = tmp_dir / "sample.pdf"
            output_path = tmp_dir / "merged.pdf"

            Image.new("RGB", (1200, 800), "red").save(image_path)

            writer = PdfWriter()
            writer.add_blank_page(width=300, height=400)
            with pdf_path.open("wb") as pdf_file:
                writer.write(pdf_file)

            warnings = export_items_to_pdf(
                [
                    MergeItem(path=image_path, item_type="image", description="Imagem"),
                    MergeItem(path=pdf_path, item_type="pdf", description="PDF"),
                ],
                output_path,
                "Média",
            )

            self.assertEqual(warnings, [])
            self.assertTrue(output_path.exists())
            self.assertEqual(len(PdfReader(str(output_path)).pages), 2)

    def test_high_compression_reduces_output_size_for_image_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / "large.jpg"
            low_path = tmp_dir / "low.pdf"
            high_path = tmp_dir / "high.pdf"

            Image.new("RGB", (3200, 2400), "blue").save(image_path, quality=95)
            item = MergeItem(path=image_path, item_type="image", description="Imagem")

            export_items_to_pdf([item], low_path, "Baixa")
            export_items_to_pdf([item], high_path, "Alta")

            self.assertTrue(high_path.stat().st_size < low_path.stat().st_size)

    def test_docx_failure_returns_warning_and_keeps_other_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / "sample.png"
            docx_path = tmp_dir / "sample.docx"
            output_path = tmp_dir / "merged.pdf"

            Image.new("RGB", (800, 600), "green").save(image_path)
            docx_path.write_bytes(b"placeholder")

            with patch(
                "juntaa.services.pdf_exporter.convert_docx_to_pdf",
                side_effect=DocxConversionError("Word não disponível"),
            ):
                warnings = export_items_to_pdf(
                    [
                        MergeItem(path=docx_path, item_type="docx", description="DOCX"),
                        MergeItem(path=image_path, item_type="image", description="Imagem"),
                    ],
                    output_path,
                    "Média",
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("Word não disponível", warnings[0])
            self.assertEqual(len(PdfReader(str(output_path)).pages), 1)

    def test_progress_callback_receives_start_and_finish_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / "sample.png"
            output_path = tmp_dir / "merged.pdf"
            updates: list[tuple[int, int, str]] = []

            Image.new("RGB", (600, 400), "orange").save(image_path)

            export_items_to_pdf(
                [MergeItem(path=image_path, item_type="image", description="Imagem")],
                output_path,
                "Média",
                progress_callback=lambda current, total, message: updates.append((current, total, message)),
            )

            self.assertEqual(len(updates), 2)
            self.assertEqual(updates[0][0:2], (0, 1))
            self.assertIn("Processando", updates[0][2])
            self.assertEqual(updates[1][0:2], (1, 1))
            self.assertIn("Concluído", updates[1][2])

    def test_invalid_compression_label_raises_export_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            image_path = tmp_dir / "sample.png"
            output_path = tmp_dir / "merged.pdf"

            Image.new("RGB", (600, 400), "black").save(image_path)

            with self.assertRaises(ExportError):
                export_items_to_pdf(
                    [MergeItem(path=image_path, item_type="image", description="Imagem")],
                    output_path,
                    "Inválida",
                )

    def test_empty_items_raise_export_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            output_path = Path(tmp_dir_name) / "merged.pdf"

            with self.assertRaises(ExportError):
                export_items_to_pdf([], output_path, "Média")


if __name__ == "__main__":
    unittest.main()
