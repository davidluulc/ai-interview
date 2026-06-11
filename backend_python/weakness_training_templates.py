from copy import deepcopy
from typing import Any


CORE_WEAK_TAGS = [
    "rag_quality",
    "rag_retrieval",
    "agent_state",
    "backend_fastapi",
    "database_modeling",
    "project_storytelling",
]


GENERIC_TEMPLATE: dict[str, Any] = {
    "weakTag": "communication_expression",
    "label": "项目表达与沟通",
    "description": "用于兜底训练候选人的结构化表达能力。",
    "coachQuestions": [
        "我们先把回答拆成三段：背景、做法、结果。你能按这个结构讲一遍吗？",
        "先不用追求完整，你先说清这个问题考察的核心概念是什么。",
    ],
    "interviewQuestions": [
        "请用背景、方案、结果的结构回答这个问题，不要只罗列技术名词。",
        "如果让你重新组织刚才的回答，你会补充哪些项目细节？",
    ],
    "difficultyLadder": {
        "basic": ["先用一句话说明这个概念解决什么问题。"],
        "medium": ["请结合项目例子说明你的做法和取舍。"],
        "hard": ["请补充验证方式、风险和后续优化方向。"],
    },
    "answerKeyPoints": ["背景", "做法", "结果", "复盘"],
    "commonMistakes": ["只罗列技术名词", "没有项目例子", "没有结果验证"],
    "oneMinuteTemplate": "可以按背景、任务、做法、结果、复盘五步组织 1 分钟回答。",
    "relatedTags": ["project_storytelling"],
}


WEAKNESS_TRAINING_TEMPLATES: dict[str, dict[str, Any]] = {
    "rag_quality": {
        "weakTag": "rag_quality",
        "label": "RAG 质量评估",
        "description": "训练候选人解释 RAG 评估指标、命中日志和质量面板。",
        "coachQuestions": [
            "我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？",
            "先不用写公式，你先说 RAG 命中日志为什么能帮助排查问题。",
        ],
        "interviewQuestions": [
            "如果你说项目里做了 RAG 质量评估，请说清 Hit@K 和 MRR 分别怎么计算。",
            "线上发现 RAG 问题质量下降时，你会先看哪些指标和日志字段？",
        ],
        "difficultyLadder": {
            "basic": ["Hit@K、MRR、关键词覆盖率分别解决什么问题？"],
            "medium": ["请结合你的项目说明 RAG 命中日志里 quality 字段如何帮助排查问题。"],
            "hard": ["如果线上发现 RAG 问题质量下降，你会如何用 Hit@K、MRR 和日志定位原因？"],
        },
        "answerKeyPoints": ["Hit@K", "MRR", "关键词覆盖率", "空召回率", "metadata 匹配率", "命中日志"],
        "commonMistakes": ["只解释字段名，不解释指标用途", "不会区分召回质量和回答质量", "没有日志排查思路"],
        "oneMinuteTemplate": "可以按指标定义、解决问题、项目落地、日志排查四步回答。",
        "relatedTags": ["rag_retrieval"],
    },
    "rag_retrieval": {
        "weakTag": "rag_retrieval",
        "label": "RAG 召回链路",
        "description": "训练候选人说明 query、chunk、BM25、向量检索、hybrid search 和 rerank 的链路。",
        "coachQuestions": [
            "先不用讲所有细节，你先按顺序说出一次 RAG 检索从 query 到 top chunks 的完整链路。",
            "BM25 和向量检索分别擅长解决什么召回问题？",
        ],
        "interviewQuestions": [
            "你项目里的 RAG 为什么先做 BM25，再做 hybrid search 和 rerank？如果 rerank 失败，系统怎么降级？",
            "请结合你的项目说明 metadata filter 在 RAG 检索里起什么作用。",
        ],
        "difficultyLadder": {
            "basic": ["一次 RAG 检索从 query 到 top chunks 大致经过哪些步骤？"],
            "medium": ["BM25、向量检索、hybrid search 和 rerank 在你的项目里分别负责什么？"],
            "hard": ["如果某个岗位问题召回错了知识库，你会从 query、metadata、rerank 哪些角度排查？"],
        },
        "answerKeyPoints": ["query 构造", "chunk 切分", "BM25", "向量检索", "hybrid search", "rerank", "metadata filter"],
        "commonMistakes": ["只说向量数据库，不讲 query 和 chunk", "不会说明 BM25 与向量检索差异", "没有降级策略"],
        "oneMinuteTemplate": "可以按 query 构造、召回、融合、重排、日志排查五步回答。",
        "relatedTags": ["rag_quality"],
    },
    "agent_state": {
        "weakTag": "agent_state",
        "label": "Agent State",
        "description": "训练候选人解释 Agent State、ToolCalls、Agent Decision、fallback、normalize、guardrail 和 nodeTrace。",
        "coachQuestions": [
            "我们先从基础开始：Agent State、ToolCalls、Agent Decision 分别解决什么问题？",
            "为什么 Agent 不能只让大模型直接自由生成下一题？",
        ],
        "interviewQuestions": [
            "请结合你的项目说明，一轮 next-question 请求里 Agent State 是怎么构造出来的。",
            "Agent Decision 如何影响最终问题生成？ToolCalls 和 nodeTrace 分别记录什么？",
        ],
        "difficultyLadder": {
            "basic": ["Agent State、ToolCalls、Agent Decision 分别是什么？"],
            "medium": ["请说明 Agent State 如何进入 Agent Decision，并影响下一题生成。"],
            "hard": ["如果模型输出非法 Agent Decision，你的 fallback、normalize 和 guardrail 如何兜底？"],
        },
        "answerKeyPoints": ["Agent State", "ToolCalls", "Agent Decision", "fallback", "normalize", "guardrail", "nodeTrace"],
        "commonMistakes": ["把 Agent 说成普通 prompt", "说不清 state 字段来源", "忽略 fallback 和日志可观测"],
        "oneMinuteTemplate": "可以按状态输入、工具调用、决策输出、兜底校验、日志追踪五步回答。",
        "relatedTags": ["rag_retrieval", "project_storytelling"],
    },
    "backend_fastapi": {
        "weakTag": "backend_fastapi",
        "label": "FastAPI 后端模块",
        "description": "训练候选人讲清 FastAPI 路由、schema、数据库会话、鉴权依赖和接口链路。",
        "coachQuestions": [
            "先按模块说：FastAPI 项目里 router、schema、db_model、database 分别负责什么？",
            "Depends(get_db) 和 Depends(get_current_user) 分别给接口注入什么能力？",
        ],
        "interviewQuestions": [
            "请解释 /api/interview/next-question 从接收请求到返回下一题，中间经过了哪些后端模块。",
            "如果接口返回 422，你会从 Pydantic schema、请求 body 和前端 payload 哪些地方排查？",
        ],
        "difficultyLadder": {
            "basic": ["router、schema、db_model、database 分别负责什么？"],
            "medium": ["请按顺序说明 next-question 接口从请求校验到调用 Agent 的后端链路。"],
            "hard": ["如果接口偶发失败，你会如何用请求日志、异常日志和 pytest 定位问题？"],
        },
        "answerKeyPoints": ["APIRouter", "Pydantic schema", "SQLAlchemy model", "database session", "Depends", "鉴权", "错误处理"],
        "commonMistakes": ["只会说 FastAPI 很快", "分不清 schema 和 model", "不知道 Depends 的作用"],
        "oneMinuteTemplate": "可以按入口路由、参数校验、依赖注入、业务调用、响应返回五步回答。",
        "relatedTags": ["database_modeling"],
    },
    "database_modeling": {
        "weakTag": "database_modeling",
        "label": "数据库建模",
        "description": "训练候选人讲清用户、投递档案、面试记录、RAG 文档、日志之间的关系。",
        "coachQuestions": [
            "先拿 interview_records 举例：这张表为什么需要 user_id？它和 users 表是什么关系？",
            "ForeignKey 和 relationship 分别解决数据库层和 Python ORM 层的什么问题？",
        ],
        "interviewQuestions": [
            "如果面试官追问你的项目如何避免用户 A 查到用户 B 的历史面试记录，你会从数据库表和查询过滤两个层面怎么回答？",
            "请解释 InterviewRecord、RagDocument、RagChunk、AgentDecisionLog 这几类表分别保存什么。",
        ],
        "difficultyLadder": {
            "basic": ["主键、外键、一对多关系分别是什么？"],
            "medium": ["为什么面试记录、RAG 文档、Agent 日志都需要 user_id？"],
            "hard": ["如果要从 SQLite 切换到生产数据库，你会如何用 Alembic 保证表结构可迁移？"],
        },
        "answerKeyPoints": ["主键", "外键", "user_id", "relationship", "数据归属", "查询过滤", "Alembic"],
        "commonMistakes": ["只知道表字段，不会讲数据归属", "把 relationship 当成数据库字段", "忽略跨用户数据隔离"],
        "oneMinuteTemplate": "可以按表职责、归属关系、查询过滤、迁移方式四步回答。",
        "relatedTags": ["backend_fastapi"],
    },
    "project_storytelling": {
        "weakTag": "project_storytelling",
        "label": "项目讲解",
        "description": "训练候选人把项目讲成业务闭环，而不是零散技术栈清单。",
        "coachQuestions": [
            "先用 1 分钟讲清：你的 AI 模拟面试系统解决谁的什么问题，核心流程是什么？",
            "不要先罗列技术栈，你先按背景、目标用户、核心流程讲一遍。",
        ],
        "interviewQuestions": [
            "请不要罗列技术栈，按背景、方案、难点、结果的顺序讲一下你为什么做这个 AI 模拟面试系统。",
            "如果我追问你的个人职责，你能说清哪些模块是你重点设计的吗？",
        ],
        "difficultyLadder": {
            "basic": ["这个项目解决谁的什么问题？"],
            "medium": ["请用背景、方案、难点、结果讲一遍项目主线。"],
            "hard": ["如果面试官质疑项目真实性，你会用哪些代码、日志、测试和部署规划证明？"],
        },
        "answerKeyPoints": ["目标用户", "业务流程", "三类 RAG", "Agent 决策", "日志可观测", "测试验证", "后续上线"],
        "commonMistakes": ["只背技术栈", "讲不出业务价值", "讲不清个人职责和验证结果"],
        "oneMinuteTemplate": "可以按目标用户、痛点、方案、工程化亮点、结果和后续规划回答。",
        "relatedTags": ["communication_expression", "agent_state"],
    },
}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def get_training_template(weak_tag: str) -> dict[str, Any]:
    key = str(weak_tag or "").strip()
    template = WEAKNESS_TRAINING_TEMPLATES.get(key)
    fallback_used = template is None
    selected = deepcopy(template or GENERIC_TEMPLATE)
    selected["fallbackUsed"] = fallback_used
    return selected


def _select_question(template: dict[str, Any], *, agent_mode: str, difficulty: str) -> str:
    ladder = template.get("difficultyLadder") if isinstance(template.get("difficultyLadder"), dict) else {}
    ladder_questions = _safe_list(ladder.get(difficulty)) or _safe_list(ladder.get("basic"))
    mode_questions = _safe_list(template.get("coachQuestions" if agent_mode == "coach" else "interviewQuestions"))
    return (ladder_questions or mode_questions or _safe_list(template.get("coachQuestions")) or [""])[0]


def select_training_template_hint(
    *,
    weakness_strategy: dict[str, Any],
    agent_mode: str,
    difficulty: str,
) -> dict[str, Any]:
    mode = "coach" if agent_mode == "coach" else "interview"
    normalized_difficulty = difficulty if difficulty in {"basic", "medium", "hard"} else "medium"
    if not isinstance(weakness_strategy, dict) or not weakness_strategy.get("enabled"):
        return {
            "enabled": False,
            "weakTag": "",
            "label": "",
            "mode": mode,
            "difficulty": normalized_difficulty,
            "recommendedQuestion": "",
            "answerKeyPoints": [],
            "commonMistakes": [],
            "oneMinuteTemplate": "",
            "relatedTags": [],
            "fallbackUsed": False,
        }

    template = get_training_template(str(weakness_strategy.get("primaryWeakTag") or ""))
    return {
        "enabled": True,
        "weakTag": template["weakTag"],
        "label": template["label"],
        "mode": mode,
        "difficulty": normalized_difficulty,
        "recommendedQuestion": _select_question(template, agent_mode=mode, difficulty=normalized_difficulty),
        "answerKeyPoints": _safe_list(template.get("answerKeyPoints"))[:6],
        "commonMistakes": _safe_list(template.get("commonMistakes"))[:4],
        "oneMinuteTemplate": str(template.get("oneMinuteTemplate") or ""),
        "relatedTags": _safe_list(template.get("relatedTags"))[:4],
        "fallbackUsed": bool(template.get("fallbackUsed")),
    }
