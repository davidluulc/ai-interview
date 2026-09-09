"""S1 public smoke: verify the structured output chain against real DashScope.

Runs in the app container with production credentials. Answers the open
question from Stage 1: does DashScope honour strict json_schema? Whatever the
outcome, the chain must return a validated model — finalStage tells which leg
won. One-off; delete after the deploy window or keep for future smoke.
"""
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic import BaseModel

from backend_python.structured_output import call_model_structured


class ProbeModel(BaseModel):
    answer: str
    confidence: int


async def main() -> None:
    model, meta = await call_model_structured(
        messages=[
            {
                "role": "user",
                "content": "用 JSON 回答：answer 用一句话说明 RAG 的作用；confidence 给 1-100 的整数。",
            }
        ],
        schema_model=ProbeModel,
        temperature=0.1,
    )
    print("finalStage:", meta["finalStage"])
    print("stages:", [(s["stage"], s["status"]) for s in meta["stages"]])
    print("answer:", model.answer[:60])
    print("confidence:", model.confidence)


if __name__ == "__main__":
    asyncio.run(main())
