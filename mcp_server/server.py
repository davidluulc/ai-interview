"""MCP server: 将 AI 面试后端的核心服务暴露为 MCP 工具。

已知限制与待办：
- 服务账号模式：所有检索固定 user_id=1（可见 user_id=1 的私有数据 + 全部公共数据）。
  多租户经 MCP 上下文传递 user_id 为后续待办（current-state 待办）。
- 每个工具独立创建 SessionLocal 并在 finally 中关闭，工具间不共享数据库会话。
- 出题/复盘工具包装 backend_python/routes/interview.py 的核心模型调用路径
  （RAG 上下文检索 + NEXT_QUESTION_SYSTEM_PROMPT/REPORT_SYSTEM_PROMPT + call_model）。
  路由层专有逻辑（限流、RAG 日志、agent 编排与守门、runtime 审计）不在 MCP 工具内
  复刻；call_model 为 async，工具内用 asyncio.run 驱动，失败自然抛出（由 MCP 上抛）。
- 工具只做既有函数的薄包装，绝不编造结果。

运行方式：仓库根目录 `python -m mcp_server.server`（或被 `from mcp_server.server
import mcp` 导入）。文件顶部的 sys.path 引导保证 `python mcp_server/server.py`
也可直接运行（与 scripts/backfill_embedding_vec.py 同一模式）。
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from backend_python.candidate_memory import (  # noqa: E402
    build_candidate_profile,
    format_candidate_memory,
    format_candidate_profile,
    retrieve_candidate_memory,
)
from backend_python.database import SessionLocal  # noqa: E402
from backend_python.llm_client import call_model  # noqa: E402
from backend_python.prompts.interview import (  # noqa: E402
    NEXT_QUESTION_SYSTEM_PROMPT,
    REPORT_SYSTEM_PROMPT,
    build_context_message,
)
from backend_python.question_rag import (  # noqa: E402
    format_question_context,
    retrieve_questions,
)
from backend_python.rag import format_role_context, retrieve_role_context  # noqa: E402
from backend_python.retrieval_service import retrieve_chunks  # noqa: E402

mcp = MCPServer("ai-interview-rag")

# 服务账号：MCP 检索统一使用 user_id=1（多租户上下文传递为后续待办）。
SERVICE_USER_ID = 1


@mcp.tool()
def retrieve_role_knowledge(query: str, limit: int = 3) -> list[dict]:
    """按查询词检索岗位知识库（BM25）。返回 title/content/score/metadata。"""
    db = SessionLocal()
    try:
        return retrieve_chunks(
            db,
            user_id=SERVICE_USER_ID,
            knowledge_base="role_knowledge",
            query=query,
            limit=limit,
            mode="bm25",
        )
    finally:
        db.close()


@mcp.tool()
def retrieve_question_bank(query: str, limit: int = 3) -> list[dict]:
    """按查询词检索题库（BM25）。返回 title/content/score/metadata。"""
    db = SessionLocal()
    try:
        return retrieve_chunks(
            db,
            user_id=SERVICE_USER_ID,
            knowledge_base="question_bank",
            query=query,
            limit=limit,
            mode="bm25",
        )
    finally:
        db.close()


@mcp.tool()
def retrieve_candidate_profile(query: str, limit: int = 3) -> list[dict]:
    """按查询词检索候选人画像知识库（BM25，KB 实名 candidate_memory）。返回 title/content/score/metadata。"""
    db = SessionLocal()
    try:
        return retrieve_chunks(
            db,
            user_id=SERVICE_USER_ID,
            knowledge_base="candidate_memory",
            query=query,
            limit=limit,
            mode="bm25",
        )
    finally:
        db.close()


@mcp.tool()
def draft_interview_question(profile_json: str, stage: str) -> dict:
    """基于候选人画像 JSON 与阶段生成下一道面试题。

    包装 routes/interview.py next_question 的核心路径：三路 RAG 上下文
    （岗位知识/题库/候选人画像，复用 retrieve_role_context / retrieve_questions /
    retrieve_candidate_memory）+ NEXT_QUESTION_SYSTEM_PROMPT + call_model
    （temperature=0.7，asyncio.run 驱动）。返回 {stage, stability, focus, prompt}。
    无 history 参数（固定空历史），路由层 agent 编排/守门/审计不复刻；
    模型未返回 prompt 时抛错（与路由行为一致）。
    """
    profile: dict[str, Any] = json.loads(profile_json)
    db = SessionLocal()
    try:
        role_hits = retrieve_role_context(profile, stage, limit=3, db=db, user_id=SERVICE_USER_ID)
        question_hits = retrieve_questions(profile, stage, limit=3, db=db, user_id=SERVICE_USER_ID)
        memories = retrieve_candidate_memory(db, profile, limit=5, user_id=SERVICE_USER_ID)
        messages = [
            {"role": "system", "content": NEXT_QUESTION_SYSTEM_PROMPT},
            build_context_message("岗位知识库 RAG 命中资料", format_role_context(role_hits)),
            build_context_message("题库 RAG 命中资料", format_question_context(question_hits)),
            build_context_message("候选人画像 RAG 命中资料", format_candidate_memory(memories)),
            build_context_message("候选人长期训练画像", format_candidate_profile(build_candidate_profile(memories))),
            {
                "role": "user",
                "content": json.dumps(
                    {"profile": profile, "history": [], "nextStage": stage},
                    ensure_ascii=False,
                ),
            },
        ]
    finally:
        db.close()
    result = asyncio.run(call_model(messages=messages, temperature=0.7))
    question = {
        "stage": str(result.get("stage") or stage),
        "stability": str(result.get("stability") or ""),
        "focus": str(result.get("focus") or ""),
        "prompt": str(result.get("prompt") or ""),
    }
    if not question["prompt"]:
        raise ValueError("Model did not return a next question.")
    return question


@mcp.tool()
def generate_interview_report(profile_json: str, answers_json: str) -> dict:
    """基于候选人画像 JSON 与逐题回答 JSON 生成面试复盘报告。

    包装 routes/interview.py interview_report 的核心路径：三路 RAG 上下文
    （与路由同参：role/question limit=4、memory limit=5、阶段“面试报告”）+
    REPORT_SYSTEM_PROMPT + call_model（temperature=0.2，asyncio.run 驱动）。
    返回模型输出的报告 JSON（score/strengths/risks/actions/questionReviews/
    trainingPlan…）；路由层后处理（build_question_reviews 等，位于 FastAPI
    路由模块）不在 MCP 工具内复刻。
    """
    profile: dict[str, Any] = json.loads(profile_json)
    answers: list[Any] = json.loads(answers_json)
    db = SessionLocal()
    try:
        role_hits = retrieve_role_context(profile, "面试报告", limit=4, db=db, user_id=SERVICE_USER_ID)
        question_hits = retrieve_questions(profile, "面试报告", limit=4, db=db, user_id=SERVICE_USER_ID)
        memories = retrieve_candidate_memory(db, profile, limit=5, user_id=SERVICE_USER_ID)
        messages = [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            build_context_message("岗位知识库 RAG 命中资料", format_role_context(role_hits)),
            build_context_message("题库 RAG 命中资料", format_question_context(question_hits)),
            build_context_message("候选人画像 RAG 命中资料", format_candidate_memory(memories)),
            build_context_message("候选人长期训练画像", format_candidate_profile(build_candidate_profile(memories))),
            {
                "role": "user",
                "content": json.dumps(
                    {"profile": profile, "answers": answers},
                    ensure_ascii=False,
                ),
            },
        ]
    finally:
        db.close()
    return asyncio.run(call_model(messages=messages, temperature=0.2))


if __name__ == "__main__":
    mcp.run()
