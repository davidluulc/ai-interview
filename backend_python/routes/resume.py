from fastapi import APIRouter, File, HTTPException, UploadFile

from ..resume_parser import parse_image_resume, parse_pdf_text

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.post("/parse")
async def parse_resume(resume: UploadFile = File(...)) -> dict[str, str]:
    file_bytes = await resume.read()
    if len(file_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file is too large.")

    content_type = resume.content_type or ""
    if content_type == "application/pdf":
        summary = parse_pdf_text(file_bytes)
        return {
            "fileName": resume.filename or "resume.pdf",
            "fileType": content_type,
            "summary": summary[:1200],
        }

    if content_type.startswith("image/"):
        summary = await parse_image_resume(resume, file_bytes)
        return {
            "fileName": resume.filename or "resume-image",
            "fileType": content_type,
            "summary": summary,
        }

    raise HTTPException(status_code=400, detail="Only PDF and image resumes are supported.")
