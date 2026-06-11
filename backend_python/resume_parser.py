import base64
import json
from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader

from .config import QWEN_VISION_MODEL
from .llm_client import call_model
from .prompts.resume import RESUME_IMAGE_SYSTEM_PROMPT, RESUME_IMAGE_USER_PROMPT


def parse_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = " ".join(pages).strip()
    return " ".join(text.split())


async def parse_image_resume(file: UploadFile, file_bytes: bytes) -> str:
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{encoded}"
    result = await call_model(
        temperature=0.2,
        model_name=QWEN_VISION_MODEL,
        messages=[
            {
                "role": "system",
                "content": RESUME_IMAGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": RESUME_IMAGE_USER_PROMPT,
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return str(result.get("summary") or "")


def build_profile_json(profile: dict, history: list | None = None, next_stage: str | None = None) -> str:
    payload = {"profile": profile}
    if history is not None:
        payload["history"] = history
    if next_stage is not None:
        payload["nextStage"] = next_stage
    return json.dumps(payload, ensure_ascii=False)
