import base64
from io import BytesIO
import os
import re

import pymupdf as fitz
from openai import AsyncOpenAI, OpenAIError
from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
MIN_EXTRACTED_TEXT = 20

IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


class DocumentExtractionError(Exception):
    pass


class DocumentExtractionUnavailable(DocumentExtractionError):
    pass


class DocumentProviderError(DocumentExtractionError):
    pass


def _vision_client() -> AsyncOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise DocumentExtractionUnavailable(
            "Image text extraction is unavailable until the AI provider is configured."
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.bazaarlink.ai/v1"),
    )


async def _read_image_with_vision(image_bytes: bytes, content_type: str) -> str:
    signatures = IMAGE_TYPES.get(content_type)
    if not signatures or not any(image_bytes.startswith(signature) for signature in signatures):
        raise DocumentExtractionError("The uploaded file is not a supported, valid image.")
    if content_type == "image/webp" and len(image_bytes) >= 12 and image_bytes[8:12] != b"WEBP":
        raise DocumentExtractionError("The uploaded file is not a valid WebP image.")
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format != IMAGE_FORMATS[content_type]:
                raise DocumentExtractionError("The image file type does not match its contents.")
            if image.width * image.height > 20_000_000:
                raise DocumentExtractionError("Images must be 20 megapixels or smaller.")
            image.verify()
    except DocumentExtractionError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise DocumentExtractionError("The uploaded image is damaged or unreadable.") from exc

    client = _vision_client()
    image_url = f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    try:
        response = await client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", os.environ.get("OPENAI_MODEL", "qwen/qwen3.7-flash:free")),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe the educational problem exactly. Preserve equations, symbols, numbering, and answer choices. Return only the transcription; do not solve it.",
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
    except OpenAIError as exc:
        raise DocumentProviderError(
            "The image could not be read by the AI provider. Check vision-model configuration or type the problem instead."
        ) from exc

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise DocumentExtractionError("No readable problem text was found in the image.")
    return text


async def extract_document_text(filename: str, content_type: str, data: bytes) -> str:
    if not data:
        raise DocumentExtractionError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentExtractionError("The file is too large. Upload a file smaller than 5 MB.")

    extension = os.path.splitext(filename)[1].lower()
    if content_type == "application/pdf" or extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentExtractionError("The uploaded file is not a valid PDF.")
        try:
            document = fitz.open(stream=data, filetype="pdf")
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise DocumentExtractionError("The PDF could not be opened. Try exporting it again.") from exc
        with document:
            if document.is_encrypted:
                raise DocumentExtractionError("Password-protected PDFs are not supported.")
            if document.page_count > MAX_PDF_PAGES:
                raise DocumentExtractionError(f"PDFs can contain at most {MAX_PDF_PAGES} pages.")
            if document.page_count < 1:
                raise DocumentExtractionError("The PDF has no pages to read.")
            transcribed_pages = []
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text").strip()
                if len(re.sub(r"\s+", "", page_text)) >= MIN_EXTRACTED_TEXT:
                    transcribed_pages.append(page_text)
                    continue
                max_dimension = max(page.rect.width, page.rect.height)
                scale = min(1.5, 3000 / max_dimension) if max_dimension else 1.0
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                page_text = await _read_image_with_vision(pixmap.tobytes("png"), "image/png")
                transcribed_pages.append(f"Page {page_number}\n{page_text}")
            return "\n\n".join(transcribed_pages)

    if content_type not in IMAGE_TYPES or extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise DocumentExtractionError("Use a PNG, JPEG, WebP, or PDF file.")
    return await _read_image_with_vision(data, content_type)
