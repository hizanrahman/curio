import unittest
from io import BytesIO
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException, UploadFile

from backend.api import problems


class ProblemExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_extracts_document_text_without_calling_an_ai_classifier(self):
        upload = UploadFile(filename="question.pdf", file=BytesIO(b"pdf"))

        with patch.object(
            problems,
            "extract_document_text",
            new=AsyncMock(return_value="What is photosynthesis?"),
        ):
            result = await problems.extract(upload, user={"id": "student"})

        self.assertEqual(result.extracted_text, "What is photosynthesis?")

    async def test_rejects_extracted_text_over_session_limit(self):
        upload = UploadFile(filename="large.pdf", file=BytesIO(b"pdf"))

        with (
            patch.object(problems, "extract_document_text", new=AsyncMock(return_value="x" * 8001)),
            self.assertRaises(HTTPException) as error,
        ):
            await problems.extract(upload, user={"id": "student"})

        self.assertEqual(error.exception.status_code, 422)
        self.assertIn("8,000", error.exception.detail)


if __name__ == "__main__":
    unittest.main()
