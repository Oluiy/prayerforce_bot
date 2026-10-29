"""Turn uploaded files into plain text."""
import io

import pypdf


class DocumentError(Exception):
    """Raised when an uploaded file can't be turned into usable text."""


class EmptyPdfError(DocumentError):
    pass


class UnreadablePdfError(DocumentError):
    pass


class NotTextFileError(DocumentError):
    pass


def is_pdf(file_name: str | None, mime_type: str | None) -> bool:
    return bool(file_name and file_name.lower().endswith(".pdf")) or bool(mime_type and "pdf" in mime_type)


def extract_text(data: bytes, file_name: str | None, mime_type: str | None) -> str:
    if is_pdf(file_name, mime_type):
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise UnreadablePdfError(str(e)) from e
        if not text.strip():
            raise EmptyPdfError("PDF has no extractable text")
        return text

    try:
        return bytes(data).decode("utf-8")
    except UnicodeDecodeError as e:
        raise NotTextFileError(str(e)) from e
