import time

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend_python.main import app


client = TestClient(app)


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def register_and_login(email: str, username: str) -> dict:
    password = "ExamplePass123!"
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def test_report_builds_question_reviews_when_model_omits_them(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        return {
            "score": 50,
            "strengths": ["能说明部分概念"],
            "risks": ["回答过短"],
            "actions": ["补充项目例子"],
        }

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-fallback-{suffix}@example.com", f"review_fb_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {
                "targetRole": "Python AI 应用实习生",
                "resume": "做过 FastAPI 和 RAG 日志",
                "jd": "需要理解 RAG 和后端接口",
                "companyNeeds": "重视学习能力",
            },
            "answers": [
                {
                    "stage": "技术追问",
                    "focus": "RAG 召回链路",
                    "question": "请解释 RAG 命中日志怎么设计？",
                    "answer": "不知道",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questionReviews"][0]["index"] == 1
    assert body["questionReviews"][0]["focus"] == "RAG 召回链路"
    assert body["questionReviews"][0]["answerStatus"] == "不会"
    assert "RAG 命中日志" in body["questionReviews"][0]["question"]
    assert body["questionReviews"][0]["trainingAction"]
    assert "rag_retrieval" in body["questionReviews"][0]["weakTags"]
    assert "rag_quality" in body["questionReviews"][0]["weakTags"]
    assert body["trainingPlan"]["shouldRetry"] is True
    assert body["trainingPlan"]["weakTopics"][0]["focus"] == "RAG 召回链路"
    assert "rag_retrieval" in body["trainingPlan"]["weakTopics"][0]["weakTags"]
    assert body["trainingPlan"]["weakTopics"][0]["trainingAction"]
    assert body["trainingPlan"]["nextRoundPriority"][0] == "RAG 召回链路"
    assert body["trainingPlan"]["practiceQuestions"]
    assert body["decisionSummary"]
    assert body["ragReasons"]


def test_report_preserves_model_question_reviews(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        return {
            "score": 80,
            "strengths": ["表达清楚"],
            "risks": ["细节略少"],
            "actions": ["补充指标"],
            "questionReviews": [
                {
                    "index": 1,
                    "focus": "后端模块设计",
                    "question": "你怎么拆 FastAPI 模块？",
                    "answerStatus": "模糊",
                    "whyAsked": "用于确认你是否理解模块边界。",
                    "missingPoints": ["路由层职责", "服务层职责"],
                    "referenceDirection": "按 router、service、model、schema 的顺序讲。",
                    "trainingAction": "画一张后端模块调用图。",
                }
            ],
            "trainingPlan": {
                "weakTopics": [
                    {
                        "focus": "后端模块设计",
                        "reason": "模块边界表达不完整。",
                        "trainingAction": "画一张后端模块调用图。",
                    }
                ],
                "nextRoundPriority": ["后端模块设计"],
                "practiceQuestions": ["请用 1 分钟说明 FastAPI 的 router、schema、model 分别负责什么。"],
                "oneMinuteTemplates": ["背景：项目需要拆模块；做法：按 router、schema、model 拆；结果：接口更清晰。"],
                "shouldRetry": True,
            },
        }

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-preserve-{suffix}@example.com", f"review_ps_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "Python 后端实习生"},
            "answers": [
                {
                    "stage": "技术问答",
                    "focus": "后端模块设计",
                    "question": "你怎么拆 FastAPI 模块？",
                    "answer": "按路由和模型拆。",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["questionReviews"][0]["whyAsked"] == "用于确认你是否理解模块边界。"
    assert body["questionReviews"][0]["missingPoints"] == ["路由层职责", "服务层职责"]
    assert "backend_fastapi" in body["questionReviews"][0]["weakTags"]
    assert body["trainingPlan"]["weakTopics"][0]["focus"] == "后端模块设计"
    assert "backend_fastapi" in body["trainingPlan"]["weakTopics"][0]["weakTags"]
    assert body["trainingPlan"]["practiceQuestions"][0].startswith("请用 1 分钟")
    assert body["trainingPlan"]["shouldRetry"] is True


def test_report_returns_fallback_when_model_times_out(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        raise HTTPException(status_code=504, detail="LLM request timed out or failed")

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-timeout-{suffix}@example.com", f"review_to_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "Python 后端实习生"},
            "answers": [
                {
                    "stage": "技术追问",
                    "focus": "RAG 命中日志",
                    "question": "在 RAG 命中日志中如何区分 BM25 和向量召回？",
                    "answer": "我不太清楚。",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 60
    assert body["fallbackUsed"] is True
    assert "模型复盘暂时不可用" in body["risks"][0]
    assert body["questionReviews"][0]["focus"] == "RAG 命中日志"
    assert body["trainingPlan"]["shouldRetry"] is True
    assert body["decisionSummary"]
    assert body["ragReasons"]


def test_report_preserves_model_explanation_fields(monkeypatch) -> None:
    async def fake_call_model(*args, **kwargs):
        return {
            "score": 82,
            "strengths": ["能结合项目回答"],
            "risks": ["RAG 证据链还不完整"],
            "actions": ["补充 RAG 命中日志字段"],
            "decisionSummary": "本轮围绕候选人项目中的 RAG 日志设计继续追问。",
            "ragReasons": ["命中岗位知识库：RAG 日志字段定位"],
            "questionReviews": [
                {
                    "index": 1,
                    "focus": "RAG 日志字段",
                    "question": "你会看哪个字段区分 BM25 和向量召回？",
                    "answerStatus": "模糊",
                    "whyAsked": "用于确认你是否真的理解 RAG 召回证据链。",
                    "missingPoints": ["matchedRetrievalModes", "bm25Score", "vectorScore"],
                    "referenceDirection": "先说字段，再说定位流程。",
                    "trainingAction": "用 1 分钟解释 RAG 命中日志字段。",
                    "weakTags": ["rag_retrieval"],
                }
            ],
            "trainingPlan": {
                "weakTopics": [
                    {
                        "focus": "RAG 日志字段",
                        "reason": "字段解释不够完整。",
                        "trainingAction": "整理 matchedRetrievalModes、bm25Score、vectorScore 的区别。",
                        "weakTags": ["rag_retrieval"],
                    }
                ],
                "nextRoundPriority": ["RAG 日志字段"],
                "practiceQuestions": ["请说明 RAG 命中日志如何区分 BM25 和向量召回。"],
                "oneMinuteTemplates": ["背景：需要定位召回质量；做法：查看 matchedRetrievalModes；结果：区分召回来源。"],
                "shouldRetry": True,
            },
        }

    monkeypatch.setattr("backend_python.routes.interview.call_model", fake_call_model)
    suffix = str(int(time.time() * 1000))
    tokens = register_and_login(f"review-explain-{suffix}@example.com", f"review_ex_{suffix[-8:]}")

    response = client.post(
        "/api/interview/report",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG 日志"},
            "answers": [
                {
                    "focus": "RAG 日志字段",
                    "question": "你会看哪个字段区分 BM25 和向量召回？",
                    "answer": "看日志里的字段，但我说不太全。",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decisionSummary"] == "本轮围绕候选人项目中的 RAG 日志设计继续追问。"
    assert body["ragReasons"] == ["命中岗位知识库：RAG 日志字段定位"]
    assert body["questionReviews"][0]["whyAsked"] == "用于确认你是否真的理解 RAG 召回证据链。"
    assert body["questionReviews"][0]["referenceDirection"] == "先说字段，再说定位流程。"


def test_report_prompt_requests_question_reviews() -> None:
    from backend_python.prompts.interview import REPORT_SYSTEM_PROMPT

    assert "questionReviews" in REPORT_SYSTEM_PROMPT
    assert "answerStatus" in REPORT_SYSTEM_PROMPT
    assert "whyAsked" in REPORT_SYSTEM_PROMPT
    assert "trainingAction" in REPORT_SYSTEM_PROMPT
    assert "trainingPlan" in REPORT_SYSTEM_PROMPT
    assert "weakTopics" in REPORT_SYSTEM_PROMPT
