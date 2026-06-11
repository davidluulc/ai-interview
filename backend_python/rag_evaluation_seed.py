from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .db_models import RagChunk, RagDocument
from .rag_store import dump_json, extract_keywords, split_content_into_chunks

EVALUATION_SEED_SOURCE = "evaluation_seed"

EVALUATION_SEED_DOCUMENTS: list[dict[str, Any]] = [
    {
        "caseId": "rag_log_fields",
        "knowledgeBase": "role_knowledge",
        "title": "RAG 日志工程化",
        "content": (
            "RAG 命中日志应该记录 query_text、retriever_name、hit_count、quality、used_in_prompt。"
            "其中 query_text 表示检索问题，retriever_name 表示召回器名称，hit_count 表示命中数量，"
            "quality 用于描述召回质量。"
        ),
        "metadata": {"category": "technical", "caseId": "rag_log_fields"},
        "embedding": [1.0, 0.0, 0.0],
    },
    {
        "caseId": "fastapi_module_split",
        "knowledgeBase": "role_knowledge",
        "title": "FastAPI 模块化",
        "content": (
            "FastAPI 后端模块化通常使用 APIRouter 拆分 routes，再把业务逻辑放到 service 层，"
            "数据库模型和 schema 单独维护，保持高内聚低耦合。"
        ),
        "metadata": {"category": "technical", "caseId": "fastapi_module_split"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "hybrid_search_reason",
        "knowledgeBase": "role_knowledge",
        "title": "Hybrid Search",
        "content": (
            "Hybrid Search 会结合 BM25 和 vector 向量检索。BM25 适合关键词精确召回，"
            "vector 适合语义召回。两路结果需要做分数归一化，并按 chunkId 去重后融合排序。"
        ),
        "metadata": {"category": "technical", "caseId": "hybrid_search_reason"},
        "embedding": [0.7, 0.7, 0.0],
    },
    {
        "caseId": "rerank_fallback",
        "knowledgeBase": "role_knowledge",
        "title": "Rerank 重排",
        "content": (
            "Rerank 重排放在 Hybrid 召回之后，用 rerankScore 重新排序候选 chunk。"
            "如果 Rerank 模型失败，系统应该降级为 Hybrid 原排序，避免影响主流程。"
        ),
        "metadata": {"category": "technical", "caseId": "rerank_fallback"},
        "embedding": [0.6, 0.3, 0.7],
    },
    {
        "caseId": "interview_follow_up",
        "knowledgeBase": "question_bank",
        "title": "面试追问策略",
        "content": (
            "AI 面试官应该根据候选人回答继续追问，重点围绕项目细节、技术取舍、失败复盘、"
            "个人职责和回答中的模糊点展开。"
        ),
        "metadata": {"category": "interview", "caseId": "interview_follow_up"},
        "embedding": [0.2, 0.4, 0.9],
    },
    {
        "caseId": "project_deep_dive",
        "knowledgeBase": "question_bank",
        "title": "项目深挖题",
        "content": "项目深挖题应围绕个人职责、技术难点、方案取舍、验证方式和复盘改进继续追问。",
        "metadata": {"category": "project", "caseId": "project_deep_dive", "interviewStage": "项目追问"},
        "embedding": [0.3, 0.5, 0.8],
    },
    {
        "caseId": "backend_dependency_question",
        "knowledgeBase": "question_bank",
        "title": "FastAPI 依赖注入题",
        "content": "FastAPI Depends 用于依赖注入，可以把鉴权、数据库会话、公共参数等能力注入到接口函数。",
        "metadata": {"category": "technical", "caseId": "backend_dependency_question", "interviewStage": "技术基础"},
        "embedding": [0.1, 0.9, 0.2],
    },
    {
        "caseId": "rag_quality_question",
        "knowledgeBase": "question_bank",
        "title": "RAG 质量评估题",
        "content": "RAG 质量评估可以追问 Hit@K、MRR、关键词覆盖率、空召回率和 metadata 匹配率。",
        "metadata": {"category": "technical", "caseId": "rag_quality_question", "interviewStage": "技术追问"},
        "embedding": [0.8, 0.2, 0.6],
    },
    {
        "caseId": "candidate_weak_rag",
        "knowledgeBase": "candidate_memory",
        "title": "候选人 RAG 薄弱点",
        "content": "候选人历史回答中多次无法说明 RAG query 构造、chunk 切分、召回质量和日志排查方式。",
        "metadata": {"category": "memory", "caseId": "candidate_weak_rag", "interviewStage": "技术追问"},
        "embedding": [0.9, 0.1, 0.4],
    },
    {
        "caseId": "candidate_backend_weakness",
        "knowledgeBase": "candidate_memory",
        "title": "候选人后端模块薄弱点",
        "content": "候选人对 FastAPI 路由、schema、db_models、database 和 Depends 的关系解释不够稳定。",
        "metadata": {"category": "memory", "caseId": "candidate_backend_weakness", "interviewStage": "后端追问"},
        "embedding": [0.2, 0.8, 0.3],
    },
    {
        "caseId": "candidate_project_expression",
        "knowledgeBase": "candidate_memory",
        "title": "候选人项目表达训练建议",
        "content": "候选人需要练习用背景、职责、方案、结果、复盘的结构讲 AI 模拟面试系统项目。",
        "metadata": {"category": "memory", "caseId": "candidate_project_expression", "interviewStage": "项目追问"},
        "embedding": [0.4, 0.4, 0.8],
    },
    {
        "caseId": "candidate_agent_learning",
        "knowledgeBase": "candidate_memory",
        "title": "候选人 Agent 学习记录",
        "content": "候选人已学习 Agent State、ToolCalls、Agent Decision 和 Orchestrator 的关系，但需要继续巩固表达。",
        "metadata": {"category": "memory", "caseId": "candidate_agent_learning", "interviewStage": "Agent 追问"},
        "embedding": [0.7, 0.3, 0.7],
    },
    {
        "caseId": "eval_py_backend_v2_001",
        "knowledgeBase": "role_knowledge",
        "title": "Python async/await 与后端 I/O",
        "content": "Python async await 适合后端 I/O 密集场景，FastAPI 路由等待数据库、HTTP 或大模型 API 时可以释放事件循环处理其他并发请求。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_001", "positionTag": "python_backend_intern", "interviewStage": "技术基础"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_002",
        "knowledgeBase": "role_knowledge",
        "title": "HTTP 请求响应与状态码",
        "content": "HTTP 请求包含 method、URL、headers 和 body，响应包含状态码和响应体。FastAPI 422 通常表示请求参数或 Pydantic schema 校验失败。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_002", "positionTag": "python_backend_intern", "interviewStage": "技术基础"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_003",
        "knowledgeBase": "role_knowledge",
        "title": "FastAPI Depends 依赖注入",
        "content": "FastAPI Depends 用于依赖注入，Depends(get_db) 注入数据库会话，Depends(get_current_user) 注入当前登录用户和鉴权能力。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_003", "positionTag": "python_backend_intern", "interviewStage": "技术基础"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_004",
        "knowledgeBase": "role_knowledge",
        "title": "Pydantic Schema 与接口校验",
        "content": "Pydantic schema 定义接口请求和响应结构，负责字段类型、必填项和默认值校验，FastAPI 参数不符合 schema 时常返回 422。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_004", "positionTag": "python_backend_intern", "interviewStage": "技术基础"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_005",
        "knowledgeBase": "role_knowledge",
        "title": "SQLAlchemy 外键与 relationship",
        "content": "SQLAlchemy ForeignKey 表示数据库表引用关系，例如 user_id 引用 users.id；relationship 提供 Python ORM 对象导航，适合表达一对多关系。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_005", "positionTag": "python_backend_intern", "interviewStage": "数据库追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_006",
        "knowledgeBase": "role_knowledge",
        "title": "数据库事务与 Alembic 迁移",
        "content": "数据库事务通过 commit 提交、rollback 回滚保证一致性。Alembic 管理数据库表结构迁移，适合记录上线环境 schema 变化。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_006", "positionTag": "python_backend_intern", "interviewStage": "数据库追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_007",
        "knowledgeBase": "role_knowledge",
        "title": "JWT 双 token 认证方案",
        "content": "JWT access token 用于短期访问接口，refresh token 用于续期并可在退出登录时撤销，后端应保存 refresh token 哈希。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_007", "positionTag": "python_backend_intern", "interviewStage": "鉴权追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_008",
        "knowledgeBase": "role_knowledge",
        "title": "用户数据隔离与权限边界",
        "content": "用户数据隔离依赖 current_user 和 user_id，保存和查询面试记录时必须按当前登录用户过滤，避免越权访问和跨用户召回。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_008", "positionTag": "python_backend_intern", "interviewStage": "鉴权追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_009",
        "knowledgeBase": "role_knowledge",
        "title": "后端日志与 pytest 测试",
        "content": "后端日志记录请求、状态码、耗时和错误，pytest 测试覆盖接口、鉴权、RAG 和 Agent，统一错误响应让前端稳定处理异常。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_009", "positionTag": "python_backend_intern", "interviewStage": "工程化追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_py_backend_v2_010",
        "knowledgeBase": "role_knowledge",
        "title": "Uvicorn、Nginx 与云服务器部署关系",
        "content": "Uvicorn 运行 FastAPI ASGI 应用，Nginx 负责公网入口、HTTPS、静态资源和反向代理，云服务器提供 Linux 运行环境。",
        "metadata": {"category": "technical", "caseId": "eval_py_backend_v2_010", "positionTag": "python_backend_intern", "interviewStage": "部署追问"},
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_001",
        "knowledgeBase": "role_knowledge",
        "title": "大模型 API 调用与参数调优",
        "content": "大模型 API 调用需要关注 temperature、JSON 输出、超时、重试和 usage，模型返回结构必须校验，失败时需要 fallback。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_001", "positionTag": "ai_app_intern", "interviewStage": "模型调用"},
        "embedding": [1.0, 0.0, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_002",
        "knowledgeBase": "role_knowledge",
        "title": "Prompt 模板化与结构化输出",
        "content": "Prompt 模板化把角色、任务、变量、few-shot 和结构化输出约束写清楚，便于后端解析 JSON 并复用不同任务。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_002", "positionTag": "ai_app_intern", "interviewStage": "Prompt 追问"},
        "embedding": [1.0, 0.0, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_003",
        "knowledgeBase": "role_knowledge",
        "title": "RAG 从文档到 prompt 的完整链路",
        "content": "RAG 链路包含 query 构造、chunk 切分、metadata 标注、召回排序和 prompt 上下文注入，用于让模型基于资料生成。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_003", "positionTag": "ai_app_intern", "interviewStage": "RAG 追问"},
        "embedding": [1.0, 0.0, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_004",
        "knowledgeBase": "role_knowledge",
        "title": "BM25、向量检索与 Hybrid Search",
        "content": "BM25 适合关键词检索，embedding vector 适合语义检索，hybrid search 融合两路召回并需要分数归一化和去重。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_004", "positionTag": "ai_app_intern", "interviewStage": "RAG 追问"},
        "embedding": [0.7, 0.7, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_005",
        "knowledgeBase": "role_knowledge",
        "title": "Rerank 与 RAG 质量评估",
        "content": "Rerank 对候选 chunk 重新排序，RAG 质量评估可用 Hit@K、MRR、关键词覆盖率、metadataMatch 和 emptyRecall。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_005", "positionTag": "ai_app_intern", "interviewStage": "RAG 评估"},
        "embedding": [0.7, 0.7, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_006",
        "knowledgeBase": "role_knowledge",
        "title": "三类 RAG 的职责边界",
        "content": "岗位知识库、题库、候选人画像三类 RAG 分别服务岗位标准、参考问题和个性化记忆，并支持权限隔离和 metadata 调试。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_006", "positionTag": "ai_app_intern", "interviewStage": "RAG 架构"},
        "embedding": [0.7, 0.7, 0.0],
    },
    {
        "caseId": "eval_ai_app_v2_007",
        "knowledgeBase": "role_knowledge",
        "title": "Agent State 与 Agent Decision",
        "content": "Agent State 是状态快照，Agent Decision 是基于状态做出的下一步决策，用于控制深挖、降难度、切换话题或结束。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_007", "positionTag": "ai_app_intern", "interviewStage": "Agent 追问"},
        "embedding": [0.0, 0.0, 1.0],
    },
    {
        "caseId": "eval_ai_app_v2_008",
        "knowledgeBase": "role_knowledge",
        "title": "ToolCalls、nodeTrace 与可观测性",
        "content": "ToolCalls 记录工具调用摘要，nodeTrace 记录 Agent 节点执行路径，二者配合日志提升 AI 应用可观测性。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_008", "positionTag": "ai_app_intern", "interviewStage": "Agent 工程化"},
        "embedding": [0.0, 0.0, 1.0],
    },
    {
        "caseId": "eval_ai_app_v2_009",
        "knowledgeBase": "role_knowledge",
        "title": "Guardrails、normalize 与 fallback",
        "content": "Guardrails 约束模型行为，normalize 校验并修正 JSON 决策字段，fallback 在模型异常或非法输出时提供规则兜底。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_009", "positionTag": "ai_app_intern", "interviewStage": "Agent 兜底"},
        "embedding": [0.0, 0.0, 1.0],
    },
    {
        "caseId": "eval_ai_app_v2_010",
        "knowledgeBase": "role_knowledge",
        "title": "LangGraph、MCP 与 Agents SDK 前沿方向",
        "content": "LangGraph 提供 StateGraph 和 checkpoint，MCP 强调 tools、resources、prompts，Agents SDK 类工具关注 tools、guardrails 和 tracing。",
        "metadata": {"category": "technical", "caseId": "eval_ai_app_v2_010", "positionTag": "ai_app_intern", "interviewStage": "前沿方向"},
        "embedding": [0.7, 0.0, 0.7],
    },
    {
        "caseId": "eval_predeploy_rag_query_rewrite",
        "knowledgeBase": "role_knowledge",
        "title": "RAG Query Rewrite 与多路召回",
        "content": "RAG query rewrite 会结合岗位、阶段、简历和上一轮回答扩展检索 query，并通过 BM25、向量检索、metadata filter 等多路召回提升检索质量。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_rag_query_rewrite",
            "positionTag": "ai_app_intern",
            "interviewStage": "RAG 追问",
        },
        "embedding": [1.0, 0.4, 0.0],
    },
    {
        "caseId": "eval_predeploy_rag_chunk_metadata",
        "knowledgeBase": "role_knowledge",
        "title": "Chunk 切分与 Metadata 设计",
        "content": "RAG chunk 应保持语义完整，metadata 记录文档名、章节、页码、权限、时间戳和版本，用于过滤、引用出处、权限隔离和调试。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_rag_chunk_metadata",
            "positionTag": "ai_app_intern",
            "interviewStage": "RAG 追问",
        },
        "embedding": [1.0, 0.5, 0.0],
    },
    {
        "caseId": "eval_predeploy_rag_quality_dashboard",
        "knowledgeBase": "role_knowledge",
        "title": "RAG 质量评估与可观测面板",
        "content": "RAG 质量评估可用 Hit@K、MRR、关键词覆盖率、metadataMatch 和 emptyRecall，并通过调试面板展示命中解释和质量摘要。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_rag_quality_dashboard",
            "positionTag": "ai_app_intern",
            "interviewStage": "RAG 评估",
        },
        "embedding": [1.0, 0.6, 0.0],
    },
    {
        "caseId": "eval_predeploy_agent_rag_collaboration",
        "knowledgeBase": "role_knowledge",
        "title": "Agent 与三类 RAG 协作",
        "content": "Agent State 汇总历史问答、上一轮回答、剩余轮次和三类 RAG 命中质量，ToolCalls 记录岗位知识库、题库和候选人画像检索结果，Agent Decision 决定深挖、降难度或切换话题。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_agent_rag_collaboration",
            "positionTag": "ai_app_intern",
            "interviewStage": "Agent 追问",
        },
        "embedding": [0.2, 0.1, 1.0],
    },
    {
        "caseId": "eval_predeploy_backend_error_logging",
        "knowledgeBase": "role_knowledge",
        "title": "FastAPI 错误处理与请求日志",
        "content": "FastAPI 后端通过 HTTPException、统一错误响应和请求日志记录路径、状态码、耗时、trace 与异常摘要，帮助线上排查 RAG、Agent 和模型调用问题。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_backend_error_logging",
            "positionTag": "python_backend_intern",
            "interviewStage": "工程化追问",
        },
        "embedding": [0.0, 1.0, 0.2],
    },
    {
        "caseId": "eval_predeploy_deployment_readiness",
        "knowledgeBase": "role_knowledge",
        "title": "上线前工程化准备",
        "content": "上线前需要规划 Uvicorn、Nginx、Redis、环境变量、生产数据库、日志和备份。Uvicorn 运行 FastAPI，Nginx 负责公网入口和反向代理，Redis 可用于缓存、token 黑名单、限流或任务队列。",
        "metadata": {
            "category": "technical",
            "caseId": "eval_predeploy_deployment_readiness",
            "positionTag": "python_backend_intern",
            "interviewStage": "部署追问",
        },
        "embedding": [0.0, 1.0, 0.4],
    },
]


def seed_evaluation_documents(db: Session, *, user_id: int = 1) -> int:
    db.execute(
        delete(RagChunk).where(
            RagChunk.user_id == user_id,
            RagChunk.metadata_json.like(f'%"{EVALUATION_SEED_SOURCE}"%'),
        )
    )
    db.execute(
        delete(RagDocument).where(
            RagDocument.user_id == user_id,
            RagDocument.source_type == EVALUATION_SEED_SOURCE,
        )
    )
    db.commit()

    created_count = 0
    for item in EVALUATION_SEED_DOCUMENTS:
        chunks = split_content_into_chunks(item["content"])
        metadata = {**item["metadata"], "source": EVALUATION_SEED_SOURCE}
        document = RagDocument(
            user_id=user_id,
            title=item["title"],
            knowledge_base=item["knowledgeBase"],
            source_type=EVALUATION_SEED_SOURCE,
            content=item["content"],
            metadata_json=dump_json(metadata),
            chunk_count=len(chunks),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        for index, chunk_content in enumerate(chunks):
            chunk = RagChunk(
                user_id=user_id,
                document_id=document.id,
                knowledge_base=item["knowledgeBase"],
                title=document.title,
                content=chunk_content,
                chunk_index=index,
                keywords_json=dump_json(extract_keywords(f"{document.title} {chunk_content}")),
                metadata_json=document.metadata_json,
                embedding_json=dump_json(item["embedding"]),
                embedding_model="evaluation-static",
                embedding_status="ready",
            )
            db.add(chunk)
        created_count += 1
    db.commit()
    return created_count
