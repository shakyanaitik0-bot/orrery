"""Getting text out of an uploaded PDF.

The README named this the missing mechanical step: `services/learning/ingest.py`
already turns text into a concept graph, so a PDF only needs to become text
upstream of that — nothing about the graph-building step changes.
"""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfExtractionError(ValueError):
    pass


def extract_text(data: bytes, max_pages: int = 60) -> str:
    """Pull plain text out of a PDF's pages, in order.

    Scanned/image-only PDFs yield little or no text — pypdf does not do OCR.
    That's surfaced as a normal `PdfExtractionError` rather than silently
    ingesting nothing.
    """
    try:
        reader = PdfReader(BytesIO(data))
    except PdfReadError as exc:
        raise PdfExtractionError(f"That doesn't look like a valid PDF: {exc}") from exc

    if reader.is_encrypted:
        # Try the empty password — plenty of "protected" PDFs are just that.
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise PdfExtractionError("This PDF is password-protected.") from exc

    pages = reader.pages[:max_pages]
    text = "\n\n".join(page.extract_text() or "" for page in pages)
    text = text.strip()

    if len(text) < 40:
        raise PdfExtractionError(
            "Couldn't find readable text in that PDF — it may be scanned "
            "images rather than text, which needs OCR this pipeline doesn't do yet."
        )
    return text
