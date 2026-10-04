import asyncio
from io import BytesIO
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import pymupdf as fitz
from PIL import Image

from backend.services.document_extractor import (
    DocumentExtractionError,
    extract_document_text,
)


class DocumentExtractionTests(unittest.TestCase):
    def test_extracts_searchable_pdf_text(self):
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "Solve the equation 3x + 7 = 22.")
        pdf_data = document.tobytes()
        document.close()

        extracted = asyncio.run(
            extract_document_text("worksheet.pdf", "application/pdf", pdf_data)
        )

        self.assertIn("3x + 7 = 22", extracted)

    def test_rejects_invalid_pdf_signature(self):
        with self.assertRaisesRegex(DocumentExtractionError, "valid PDF"):
            asyncio.run(
                extract_document_text("worksheet.pdf", "application/pdf", b"not a PDF")
            )

    def test_rejects_oversized_upload(self):
        with self.assertRaisesRegex(DocumentExtractionError, "too large"):
            asyncio.run(
                extract_document_text(
                    "problem.png",
                    "image/png",
                    b"x" * (5 * 1024 * 1024 + 1),
                )
            )

    def test_uses_vision_for_valid_image(self):
        vision_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Solve 3x + 7 = 22."))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(return_value=vision_response))
            )
        )
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), "white").save(image_buffer, format="PNG")
        png_bytes = image_buffer.getvalue()
        with patch(
            "backend.services.document_extractor._vision_client",
            return_value=client,
        ):
            extracted = asyncio.run(
                extract_document_text("problem.png", "image/png", png_bytes)
            )

        self.assertEqual(extracted, "Solve 3x + 7 = 22.")
        client.chat.completions.create.assert_awaited_once()

    def test_rejects_malformed_image_even_with_png_mime_type(self):
        with self.assertRaisesRegex(DocumentExtractionError, "damaged or unreadable"):
            asyncio.run(
                extract_document_text(
                    "problem.png",
                    "image/png",
                    b"\x89PNG\r\n\x1a\nnot an image",
                )
            )

    def test_uses_vision_for_scanned_pdf_pages(self):
        document = fitz.open()
        document.new_page()
        pdf_data = document.tobytes()
        document.close()
        with patch(
            "backend.services.document_extractor._read_image_with_vision",
            new=AsyncMock(return_value="Solve 3x + 7 = 22."),
        ) as read_page:
            extracted = asyncio.run(
                extract_document_text("scan.pdf", "application/pdf", pdf_data)
            )

        self.assertIn("Page 1", extracted)
        self.assertIn("3x + 7 = 22", extracted)
        read_page.assert_awaited_once()

    def test_uses_vision_for_scanned_pages_in_mixed_pdf(self):
        document = fitz.open()
        text_page = document.new_page()
        text_page.insert_text((72, 72), "Solve this equation: 2x + 4 = 14.")
        document.new_page()
        pdf_data = document.tobytes()
        document.close()
        with patch(
            "backend.services.document_extractor._read_image_with_vision",
            new=AsyncMock(return_value="Find the area of the pictured triangle."),
        ) as read_page:
            extracted = asyncio.run(
                extract_document_text("mixed.pdf", "application/pdf", pdf_data)
            )

        self.assertIn("2x + 4 = 14", extracted)
        self.assertIn("pictured triangle", extracted)
        read_page.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
