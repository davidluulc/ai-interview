import asyncio
from typing import Any

from sqlalchemy.orm import Session

from .db_models import RagChunk, RagDocument
from .embedding_client import current_embedding_model, embed_text
from .rag_store import (
    build_chunk_hash_records,
    compute_text_hash,
    dump_json,
    extract_keywords,
    parse_json,
    split_content_into_chunks,
)


PRODUCTION_RAG_SEED_ITEMS: list[dict[str, Any]] = [
    {
        "seedKey": "role-python-fastapi-rag-v1",
        "knowledgeBase": "role_knowledge",
        "title": "Python 后端与 FastAPI 岗位知识",
        "content": (
            "Python 后端实习岗位常考函数、异常、类型标注、面向对象、模块拆分和工程化测试。"
            "FastAPI 项目重点关注路由设计、依赖注入、Pydantic schema、鉴权依赖、中间件、异常处理和接口分层。"
            "\n\n回答项目题时，应说明业务背景、接口职责、数据库模型、错误处理、测试覆盖和部署方式。"
            "如果被追问 Depends，可以从依赖复用、权限校验、数据库 Session 生命周期和可测试性展开。"
        ),
        "metadata": {
            "seedKey": "role-python-fastapi-rag-v1",
            "positionTag": "python_backend_intern",
            "category": "technical",
            "interviewStage": "技术基础",
            "source": "production_seed",
        },
    },
    {
        "seedKey": "role-rag-agent-langgraph-v1",
        "knowledgeBase": "role_knowledge",
        "title": "RAG Agent 与 LangGraph 项目知识",
        "content": (
            "RAG 工程链路包括 query 构建、chunk 切分、metadata 标注、BM25 关键词召回、向量召回、hybrid search、rerank 和 prompt 注入控制。"
            "RAG 命中日志需要记录 query、知识库名称、检索模式、命中数量、命中 JSON、是否进入 prompt 和质量原因。"
            "\n\nAgent 工程链路包括 observe_state、retrieve_context、analyze_answer、apply_policy、generate_question 和 fallback。"
            "policy 用来控制模式、难度和话题迁移，guardrail 用来防止非法动作、重复问题和无限深挖，fallback 用来兜底不合法决策。"
        ),
        "metadata": {
            "seedKey": "role-rag-agent-langgraph-v1",
            "positionTag": "ai_app_intern",
            "category": "technical",
            "interviewStage": "项目深挖",
            "source": "production_seed",
        },
    },
    {
        "seedKey": "role-rag-log-fields-v1",
        "knowledgeBase": "role_knowledge",
        "title": "RAG 命中日志字段定位",
        "content": (
            "RAG 命中日志用于解释一次问题为什么会命中某些资料，也用于排查空召回和错召回。"
            "核心字段包括 queryText、retrieverName、retrievalMode、matchedRetrievalModes、hitCount、hitsJson、usedInPrompt 和 qualityReason。"
            "\n\nretrievalMode 表示本次检索总体采用 keyword、vector、hybrid 还是 rerank。"
            "matchedRetrievalModes 用于说明某条命中结果来自 BM25 关键词召回、向量召回还是两者同时命中。"
            "如果要区分 BM25 和向量召回，应优先查看 matchedRetrievalModes；排查排序时再看 bm25Score、vectorScore 和 rerankScore。"
            "\n\nbm25Score 体现关键词匹配强度，适合排查岗位名、技术词、字段名是否命中；"
            "vectorScore 体现语义相似度，适合排查同义表达是否命中；"
            "rerankScore 体现重排模型最终判断。面试中回答这类问题时，应先说字段职责，再举一个日志排查例子。"
        ),
        "metadata": {
            "seedKey": "role-rag-log-fields-v1",
            "positionTag": "ai_app_intern",
            "category": "technical",
            "interviewStage": "RAG 日志定位",
            "source": "production_seed",
            "tags": ["rag", "bm25", "vector", "retrievalMode", "matchedRetrievalModes"],
        },
    },
    {
        "seedKey": "question-rag-quality-v1",
        "knowledgeBase": "question_bank",
        "title": "RAG 质量评估题库",
        "content": (
            "请解释 RAG 命中日志应该记录哪些字段，以及这些字段如何帮助排查空召回、召回错误和 prompt 注入失败。"
            "\n\n如果某个岗位问题没有召回资料，你会按什么顺序排查？请从知识库是否有资料、query 构建、metadata filter、向量模型、rerank 和日志证据展开。"
            "\n\nHit@K 和 MRR 分别衡量什么？为什么只看命中数量不够，还要看正确结果是否足够靠前？"
        ),
        "metadata": {
            "seedKey": "question-rag-quality-v1",
            "positionTag": "ai_app_intern",
            "category": "interview_question",
            "difficulty": "standard",
            "interviewStage": "RAG 追问",
            "source": "production_seed",
        },
    },
    {
        "seedKey": "question-rag-log-fields-v1",
        "knowledgeBase": "question_bank",
        "title": "BM25 与向量召回日志字段题",
        "content": (
            "面试题：在 RAG 命中日志中，你会查看哪个字段来区分是 BM25 还是向量召回的结果？"
            "参考回答：先看 matchedRetrievalModes，因为它记录每条 hit 是 keyword/BM25、vector 还是 hybrid 命中；"
            "再结合 retrievalMode 判断本次检索链路整体模式。"
            "\n\n如果需要进一步解释排序差异，可以补充 bm25Score、vectorScore、rerankScore："
            "bm25Score 偏关键词覆盖，vectorScore 偏语义相似，rerankScore 是重排后的最终相关性判断。"
            "最后说明 hitsJson 保存命中文档、chunk、score 和 metadata，usedInPrompt 表示是否真正进入提示词。"
        ),
        "metadata": {
            "seedKey": "question-rag-log-fields-v1",
            "positionTag": "ai_app_intern",
            "category": "interview_question",
            "difficulty": "standard",
            "interviewStage": "RAG 日志定位",
            "source": "production_seed",
            "tags": ["rag", "bm25", "vector", "retrievalMode", "matchedRetrievalModes"],
        },
    },
    {
        "seedKey": "question-backend-production-v1",
        "knowledgeBase": "question_bank",
        "title": "后端生产化题库",
        "content": (
            "为什么要把 RAG 文档入库从 HTTP 请求链路拆到 Celery worker？请说明用户体验、超时风险、失败重试和任务状态可观测性。"
            "\n\nPostgreSQL、Redis、Celery 在这个项目里分别承担什么职责？为什么本地开发可以保留 SQLite，但生产环境要兼容 PostgreSQL？"
            "\n\n如果 Nginx 返回 504，但 FastAPI 日志最终显示 200，你会如何判断是服务崩溃、上游超时还是模型响应过慢？"
        ),
        "metadata": {
            "seedKey": "question-backend-production-v1",
            "positionTag": "python_backend_intern",
            "category": "interview_question",
            "difficulty": "standard",
            "interviewStage": "工程化追问",
            "source": "production_seed",
        },
    },
]


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def seed_key_exists(db: Session, *, user_id: int, seed_key: str) -> bool:
    documents = (
        db.query(RagDocument)
        .filter(RagDocument.user_id == user_id, RagDocument.source_type == "production_seed")
        .all()
    )
    for document in documents:
        metadata = parse_json(document.metadata_json, {})
        if metadata.get("seedKey") == seed_key:
            return True
    return False


def create_seed_document(db: Session, *, user_id: int, item: dict[str, Any]) -> RagDocument:
    content = str(item["content"]).strip()
    metadata = dict(item["metadata"])
    chunks = split_content_into_chunks(content)
    chunk_records = build_chunk_hash_records(chunks)
    document = RagDocument(
        user_id=user_id,
        title=str(item["title"]).strip(),
        knowledge_base=str(item["knowledgeBase"]),
        source_type="production_seed",
        status="enabled",
        visibility="public",
        content_hash=compute_text_hash(content),
        content=content,
        metadata_json=dump_json(metadata),
        chunk_count=len(chunks),
        duplicate_chunk_count=sum(1 for chunk in chunk_records if chunk["isDuplicate"]),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    embedding_model = current_embedding_model()
    for index, chunk_record in enumerate(chunk_records):
        chunk_content = str(chunk_record["content"])
        embedding: list[float] = []
        embedding_status = "pending"
        try:
            embedding = run_async(embed_text(chunk_content))
            embedding_status = "ready" if embedding else "empty"
        except Exception:
            embedding_status = "failed"

        chunk = RagChunk(
            user_id=user_id,
            document_id=document.id,
            knowledge_base=str(item["knowledgeBase"]),
            title=document.title,
            content=chunk_content,
            chunk_index=index,
            chunk_hash=str(chunk_record["hash"]),
            is_duplicate=1 if chunk_record["isDuplicate"] else 0,
            keywords_json=dump_json(extract_keywords(f"{document.title} {chunk_content}")),
            metadata_json=document.metadata_json,
            embedding_json=dump_json(embedding),
            embedding_model=embedding_model if embedding_status == "ready" else "",
            embedding_status=embedding_status,
        )
        db.add(chunk)
    db.commit()
    db.refresh(document)
    return document


def summarize_seed_chunks(db: Session, *, user_id: int) -> dict[str, int]:
    chunks = (
        db.query(RagChunk)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RagChunk.user_id == user_id, RagDocument.source_type == "production_seed")
        .all()
    )
    return {
        "totalChunks": len(chunks),
        "readyChunks": sum(1 for chunk in chunks if chunk.embedding_status == "ready"),
        "failedChunks": sum(1 for chunk in chunks if chunk.embedding_status == "failed"),
    }


def run_production_rag_seed(db: Session, *, user_id: int) -> dict[str, Any]:
    created_documents = 0
    skipped_documents = 0
    for item in PRODUCTION_RAG_SEED_ITEMS:
        seed_key = str(item["seedKey"])
        if seed_key_exists(db, user_id=user_id, seed_key=seed_key):
            skipped_documents += 1
            continue
        create_seed_document(db, user_id=user_id, item=item)
        created_documents += 1

    chunk_summary = summarize_seed_chunks(db, user_id=user_id)
    return {
        "createdDocuments": created_documents,
        "skippedDocuments": skipped_documents,
        "seedDocuments": len(PRODUCTION_RAG_SEED_ITEMS),
        **chunk_summary,
    }
