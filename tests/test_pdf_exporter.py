from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader, PdfWriter

from juntaa.models import MergeItem
from juntaa.services.pdf_exporter import export_items_to_pdf
from juntaa.converters.docx_adapter import DocxConversionError


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


if __name__ == "__main__":
    unittest.main()
