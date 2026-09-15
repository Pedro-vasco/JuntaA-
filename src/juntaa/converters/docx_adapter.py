from __future__ import annotations

from base64 import b64encode
import logging
from pathlib import Path
import platform
import subprocess

from docx import Document

LOGGER = logging.getLogger(__name__)


class DocxConversionError(RuntimeError):
    pass


def describe_docx(path: Path) -> str:
    document = Document(path)
    non_empty_paragraphs = sum(1 for paragraph in document.paragraphs if paragraph.text.strip())
    return f"DOCX • {non_empty_paragraphs} parágrafos"


def convert_docx_to_pdf(source: Path, destination: Path) -> Path:
    if platform.system() != "Windows":
        raise DocxConversionError(
            "A conversão de DOCX para PDF neste MVP requer Windows com Microsoft Word disponível."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $document = $word.Documents.Open('{str(source.resolve()).replace("'", "''")}')
    $document.SaveAs('{str(destination.resolve()).replace("'", "''")}', 17)
}}
finally {{
    if ($document -ne $null) {{ $document.Close() }}
    if ($word -ne $null) {{ $word.Quit() }}
    if ($document -ne $null) {{ [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }}
    if ($word -ne $null) {{ [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }}
}}
""".strip()
    encoded_script = b64encode(script.encode("utf-16le")).decode("ascii")

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise DocxConversionError(
            "PowerShell não foi encontrado. Use Windows 10/11 com Microsoft Word para converter DOCX."
        ) from exc
    except subprocess.CalledProcessError as exc:
        LOGGER.exception("Falha ao converter DOCX: %s", source)
        stderr = (exc.stderr or "").strip()
        if stderr:
            LOGGER.error("Detalhe do PowerShell/Word para %s: %s", source, stderr)
        raise DocxConversionError(
            "Não foi possível converter o arquivo DOCX. Verifique se o Microsoft Word está instalado e acessível."
        ) from exc

    return destination
