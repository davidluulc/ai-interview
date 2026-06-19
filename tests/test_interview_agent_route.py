import json
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, User
from backend_python.main import app


def test_question_strategy_payload_includes_mode_guidance() -> None:
    from backend_python.routes.interview import build_question_strategy_payload

    coach_payload = build_question_strategy_payload(
        history=[{"question": "请写 RAG 日志 JSON", "answer": "不知道"}],
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        agent_mode="coach",
    )
    interview_payload = build_question_strategy_payload(
        history=[{"question": "请解释 RAG 日志字段", "answer": "不知道"}],
        role_hits=[],
        question_hits=[],
        memory_hits=[],
        agent_mode="interview",
    )

    assert coach_payload["questionStrategy"]["modeGuidance"]["mode"] == "coach"
    assert "拆小" in coach_payload["questionStrategy"]["modeGuidance"]["style"]
    assert "回答框架" in coach_payload["questionStrategy"]["modeGuidance"]["weakAnswerGuidance"]
    assert interview_payload["questionStrategy"]["modeGuidance"]["mode"] == "interview"
    assert "压力" in interview_payload["questionStrategy"]["modeGuidance"]["style"]
    assert "切换到相邻话题" in interview_payload["questionStrategy"]["modeGuidance"]["weakAnswerGuidance"]


def test_next_question_writes_agent_decision_log(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 日志字段",
                "reason": "候选人回答不知道，需要先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 日志字段",
            "prompt": "我们先降低难度：RAG 命中日志通常记录哪些字段？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-route-{suffix}@example.com"
    username = f"agent_route_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        before_count = db.scalar(select(func.count()).select_from(AgentDecisionLog).where(AgentDecisionLog.user_id == user_id))

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [{"question": "RAG 日志怎么写？", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agentDecision"]["nextAction"] == "lower_difficulty"
    assert body["agentDecision"]["agentMode"] == "coach"
    assert body["decisionSummary"]
    assert body["ragReasons"]
    assert any("岗位知识库" in reason for reason in body["ragReasons"])
    with SessionLocal() as db:
        logs = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).all()
        after_count = db.scalar(select(func.count()).select_from(AgentDecisionLog).where(AgentDecisionLog.user_id == user_id))

    assert logs
    assert after_count == before_count + 1
    assert logs[0].next_action == "lower_difficulty"
    assert logs[0].request_type == "next_question"
    assert logs[0].decision_json
    assert '"agentMode": "coach"' in logs[0].decision_json
    assert '"toolCalls"' in logs[0].state_json
    assert '"retrieve_role_knowledge"' in logs[0].state_json
    assert '"toolCalls"' in logs[0].decision_json
    decision_json = json.loads(logs[0].decision_json)
    node_names = [item["nodeName"] for item in decision_json["nodeTrace"]]
    assert node_names == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "select_weakness_strategy",
        "apply_policy",
        "select_training_template",
        "select_action",
        "generate_question",
        "update_memory",
    ]
    assert decision_json["policy"]["recommendedAction"] == "lower_difficulty"
    generate_trace = decision_json["nodeTrace"][-2]
    assert generate_trace["outputSummary"]["stage"] == body["stage"]
    assert generate_trace["outputSummary"]["focus"] == body["focus"]
    assert generate_trace["outputSummary"]["promptLength"] == len(body["prompt"])
    assert generate_trace["inputSummary"]["decisionFocus"] == "RAG 日志字段"
    update_memory_trace = decision_json["nodeTrace"][-1]
    assert update_memory_trace["outputSummary"]["shouldUpdateMemory"] is True
    assert update_memory_trace["outputSummary"]["status"] == "deferred"


def test_next_question_normalizes_generic_focus_and_softens_hard_weak_answer_prompt(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 日志字段",
                "reason": "候选人回答不知道，需要先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "项目背景",
            "stability": "动态追问",
            "focus": "项目背景",
            "prompt": "请现场写出一条完整 RAG 命中日志 JSON，必须包含 hits_json 和 quality。",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-normalize-{suffix}@example.com"
    username = f"agent_norm_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 命中日志"},
            "history": [{"question": "请写 RAG 日志 JSON", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["focus"] == "RAG 召回链路"
    assert "完整 RAG 命中日志 JSON" not in body["prompt"]
    assert "必须包含" not in body["prompt"]
    assert "先拆小一点" in body["prompt"]
    assert "query" in body["prompt"]


def test_first_question_does_not_use_weak_answer_wording(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "开场问题",
                "difficulty": "basic",
                "focus": "RAG 基础",
                "reason": "候选人上一轮回答偏弱，先降低难度确认基础概念。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": False,
                "agentMode": "coach",
            }
        return {
            "stage": "开场问题",
            "stability": "开场题",
            "focus": "RAG 基础",
            "prompt": "我们先把难度降下来：你能用自己的话解释 RAG 为什么需要检索、重排和引用来源吗？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"opening-question-{suffix}@example.com"
    username = f"opening_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "难度降" not in body["prompt"]
    assert "上一轮回答" not in body["decisionSummary"]
    assert body["agentDecision"]["nextAction"] == "deep_follow_up"
    assert "opening_question" in body["agentDecision"]["triggerRules"]


def test_next_question_sends_mode_guidance_to_question_model(monkeypatch) -> None:
    from backend_python.routes import interview

    captured_question_payloads = []

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 日志字段",
                "reason": "候选人回答不知道，需要先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        captured_question_payloads.append(json.loads(messages[-1]["content"]))
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 日志字段",
            "prompt": "我们先拆小一点：query_text 表示什么？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-mode-payload-{suffix}@example.com"
    username = f"agent_mode_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [{"question": "RAG 日志怎么写？", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    assert captured_question_payloads
    mode_guidance = captured_question_payloads[0]["questionStrategy"]["modeGuidance"]
    assert mode_guidance["mode"] == "coach"
    assert "学习辅导模式" in mode_guidance["style"]
    assert "更小的问题" in mode_guidance["weakAnswerGuidance"]


def test_next_question_rewrites_repeated_prompt_from_model(monkeypatch) -> None:
    from backend_python.routes import interview

    repeated_prompt = "请解释 RAG 命中日志怎么设计？"

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "switch_topic",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 召回链路",
                "reason": "候选人连续答不上来，应该切换到相邻考察点。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 召回链路",
            "prompt": repeated_prompt,
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-repeat-{suffix}@example.com"
    username = f"agent_repeat_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 命中日志和 FastAPI 接口"},
            "history": [{"question": repeated_prompt, "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"] != repeated_prompt
    assert "换个角度" in body["prompt"]
    assert body["focus"] != "RAG 召回链路"
    assert "repeated_prompt_guardrail" in body["agentDecision"]["triggerRules"]
    assert body["agentDecision"]["guardrailApplied"] is True
    assert body["agentDecision"]["topicShift"]["from"] != body["focus"]
    assert body["agentDecision"]["topicShift"]["to"] == body["focus"]
    assert body["agentDecision"]["debugSignals"]["guardrailApplied"] is True
    assert body["agentDecision"]["debugSignals"]["topicShifted"] is True
    assert "repeated_prompt_guardrail" in body["agentDecision"]["debugSignals"]["triggerRules"]
    assert "检测到模型生成了重复问题" in body["decisionSummary"]

    with SessionLocal() as db:
        log = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).first()

    assert log is not None
    assert '"guardrailApplied": true' in log.decision_json
    assert '"topicShift"' in log.decision_json
    assert '"debugSignals"' in log.decision_json
    assert '"repeated_prompt_guardrail"' in log.decision_json


def test_next_question_uses_frequent_weak_tags_in_agent_strategy(monkeypatch) -> None:
    from backend_python.routes import interview

    captured_question_payloads = []

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 质量评估",
                "reason": "模型返回基础降难度，normalize 应保留 weaknessStrategy。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        captured_question_payloads.append(json.loads(messages[-1]["content"]))
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 质量评估",
            "prompt": "我们先拆小一点：Hit@K、MRR、关键词覆盖率分别解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"weakness-route-{suffix}@example.com"
    username = f"weakness_route_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    client.post(
        "/api/history",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"candidateName": "测试用户", "targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
            "answers": [{"stage": "技术追问", "focus": "RAG 质量评估", "question": "Hit@K 是什么？", "answer": "不知道"}],
            "report": {
                "score": 55,
                "risks": ["RAG 质量评估表达薄弱"],
                "actions": ["复习 Hit@K、MRR、关键词覆盖率"],
                "questionReviews": [{"focus": "RAG 质量评估", "weakTags": ["rag_quality"]}],
                "trainingPlan": {"weakTopics": [{"focus": "RAG 质量评估", "weakTags": ["rag_quality"]}]},
            },
        },
    )

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 质量评估"},
            "history": [{"question": "RAG 质量怎么评估？", "answer": "不清楚", "focus": "RAG 质量评估"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    body = response.json()
    strategy = body["agentDecision"]["weaknessStrategy"]
    assert strategy["enabled"] is True
    assert strategy["primaryWeakTag"] == "rag_quality"
    assert strategy["modePolicy"] == "coach_remediation"
    assert "weakness_strategy" in body["agentDecision"]["triggerRules"]
    assert "RAG 质量评估" in body["decisionSummary"]
    template_hint = body["agentDecision"]["trainingTemplateHint"]
    assert template_hint["enabled"] is True
    assert template_hint["weakTag"] == "rag_quality"
    assert "Hit@K" in template_hint["recommendedQuestion"]
    assert captured_question_payloads[0]["agentDecision"]["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert captured_question_payloads[0]["questionStrategy"]["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert captured_question_payloads[0]["agentDecision"]["trainingTemplateHint"]["weakTag"] == "rag_quality"
    assert captured_question_payloads[0]["questionStrategy"]["trainingTemplateHint"]["weakTag"] == "rag_quality"

    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        log = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).first()

    assert log is not None
    state_json = json.loads(log.state_json)
    decision_json = json.loads(log.decision_json)
    assert state_json["candidateProfile"]["frequentWeakTags"][0] == "rag_quality"
    assert decision_json["weaknessStrategy"]["primaryWeakTag"] == "rag_quality"
    assert decision_json["trainingTemplateHint"]["weakTag"] == "rag_quality"
    assert "select_weakness_strategy" in [item["nodeName"] for item in decision_json["nodeTrace"]]
    assert "select_training_template" in [item["nodeName"] for item in decision_json["nodeTrace"]]


def test_next_question_defaults_to_classic_when_agent_runtime_missing(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "FastAPI Depends",
                "reason": "候选人回答较短，先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "FastAPI Depends",
            "prompt": "我们先拆小一点：Depends 在 FastAPI 里解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-default-{suffix}@example.com"
    username = f"runtime_default_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "Python 后端开发实习生", "resume": "做过 FastAPI"},
            "history": [{"question": "Depends 是什么？", "answer": "依赖注入"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"]
    assert body["runtimeAudit"]["requestedRuntime"] == "classic"
    assert body["runtimeAudit"]["allowedRuntime"] == "classic"
    assert body["runtimeAudit"]["visibleRuntime"] == "classic"


def test_normal_user_langgraph_canary_request_is_downgraded(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "LangGraph 灰度",
                "reason": "普通用户请求实验链路时应由策略层降级。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "LangGraph 灰度",
            "prompt": "我们先解释一下：灰度发布为什么要保留 fallback？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-user-{suffix}@example.com"
    username = f"runtime_user_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "学习 LangGraph"},
            "history": [{"question": "LangGraph 是什么？", "answer": "工作流框架"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "langgraph_canary",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert body["runtimeAudit"]["allowedRuntime"] == "classic"
    assert body["runtimeAudit"]["visibleRuntime"] == "classic"
    assert "普通用户暂不开放 LangGraph 灰度链路" in body["runtimeAudit"]["policyReasons"]


def test_admin_langgraph_canary_uses_real_generated_question_instead_of_poc_prompt(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "LangGraph checkpoint",
                "reason": "管理员灰度链路允许 LangGraph 生成可见问题。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "LangGraph checkpoint",
            "prompt": "classic fallback question",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-admin-{suffix}@example.com"
    username = f"runtime_admin_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "学习 LangGraph checkpoint"},
            "history": [{"question": "LangGraph checkpoint 是什么？", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "langgraph_canary",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"] == "classic fallback question"
    assert "RAG 为什么需要检索" not in body["prompt"]
    assert body["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert body["runtimeAudit"]["allowedRuntime"] == "langgraph"
    assert body["runtimeAudit"]["visibleRuntime"] == "langgraph"
    assert body["runtimeAudit"]["fallbackUsed"] is False


def test_next_question_returns_safe_fallback_when_question_model_provider_fails(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "LangGraph 灰度迁移",
                "reason": "候选人回答较短，先降低难度继续追问。",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        raise HTTPException(status_code=502, detail="LLM provider request failed.")

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"runtime-provider-fallback-{suffix}@example.com"
    username = f"runtime_provider_{suffix[:8]}"

    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 LangGraph 灰度迁移"},
            "history": [{"question": "为什么要灰度迁移？", "answer": "为了稳一点"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
            "agentRuntime": "classic",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prompt"]
    assert "模型服务暂时不可用" in body["prompt"]
    assert body["agentDecision"]["fallbackUsed"] is True
    assert "model_provider_fallback" in body["agentDecision"]["triggerRules"]
    assert body["runtimeAudit"]["visibleRuntime"] == "classic"
    assert body["runtimeAudit"]["fallbackUsed"] is True
    assert "模型供应商请求失败" in body["runtimeAudit"]["qualityGateReasons"]
