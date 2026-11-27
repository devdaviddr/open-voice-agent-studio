"""Turn an uploaded file into plain text."""

import io
from pathlib import PurePath

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_BYTES = 20 * 1024 * 1024

# extension -> mime type the studio accepts (MVP FR-15: Markdown, text and PDF)
ACCEPTED = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
}


class ParseError(ValueError):
    """The file cannot be read as text; the message is shown to the user."""


def mime_for(filename: str) -> str | None:
    return ACCEPTED.get(PurePath(filename).suffix.lower())


def extract_text(content: bytes, mime: str) -> str:
    if mime == "application/pdf":
        if not content.startswith(b"%PDF"):
            raise ParseError("This file is not a valid PDF.")
        try:
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        except PdfReadError as e:
            raise ParseError(f"The PDF could not be read: {e}") from e
    else:
        text = content.decode("utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ParseError("No text was found in this file (a scanned PDF needs OCR first).")
    return text
