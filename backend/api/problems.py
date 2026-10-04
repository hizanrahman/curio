from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.document_extractor import (
    DocumentExtractionError,
    DocumentExtractionUnavailable,
    DocumentProviderError,
    MAX_UPLOAD_BYTES,
    extract_document_text,
)
from backend.services.authentication import get_current_user

router = APIRouter()


class ExtractedProblem(BaseModel):
    extracted_text: str


@router.get("/test")
def test_endpoint():
    return {"status": "reloaded"}

@router.post("/extract", response_model=ExtractedProblem)
async def extract(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="The uploaded file needs a filename.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        content = await extract_document_text(file.filename, file.content_type or "", data)
    except DocumentExtractionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DocumentProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()

    if len(content) > 8000:
        raise HTTPException(status_code=422, detail="A problem must be 8,000 characters or shorter.")
    return ExtractedProblem(extracted_text=content)
