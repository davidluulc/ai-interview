import json
from uuid import uuid4

from backend_python.candidate_memory import build_candidate_profile, format_candidate_profile, retrieve_candidate_memory
from backend_python.database import SessionLocal
from backend_python.db_models import InterviewRecord, User


def create_user(db, email: str) -> User:
    user = User(email=email, username=email.split("@")[0], password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_record(
    db,
    *,
    user_id: int,
    application_profile_id: int | None,
    target_role: str,
    score: int,
    risk: str,
    report_extra: dict | None = None,
) -> InterviewRecord:
    report = {"risks": [risk], "actions": [f"改进：{risk}"]}
    if report_extra:
        report.update(report_extra)
    record = InterviewRecord(
        user_id=user_id,
        application_profile_id=application_profile_id,
        candidate_name="David",
        target_role=target_role,
        application_type="实习投递",
        mode="技术一面",
        depth="standard",
        score=score,
        profile_json=json.dumps({"targetRole": target_role}, ensure_ascii=False),
        answers_json=json.dumps([{"stage": "技术追问", "answer": risk}], ensure_ascii=False),
        report_json=json.dumps(report, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_build_candidate_profile_returns_empty_profile_without_memories() -> None:
    profile = build_candidate_profile([])

    assert profile == {
        "hasHistory": False,
        "scoreTrend": [],
        "averageScore": 0,
        "latestScore": 0,
        "bestScore": 0,
        "recentRisks": [],
            "frequentRisks": [],
            "frequentActions": [],
            "frequentWeakTags": [],
            "weakStages": [],
            "trainingFocus": [],
        }


def test_build_candidate_profile_aggregates_scores_and_training_focus() -> None:
    memories = [
        {
            "targetRole": "AI 应用开发实习生",
            "score": 82,
            "risks": ["RAG 原理解释不够清晰", "项目部署链路薄弱"],
            "actions": ["复盘 RAG 检索流程", "补充 Docker 部署练习"],
            "recentStages": ["技术追问", "项目深挖"],
        },
        {
            "targetRole": "AI 应用开发实习生",
            "score": 76,
            "risks": ["RAG 原理解释不够清晰", "数据库设计表达薄弱"],
            "actions": ["复盘 RAG 检索流程", "梳理 SQLAlchemy 表关系"],
            "recentStages": ["技术追问", "项目深挖"],
        },
        {
            "targetRole": "Python 后端实习生",
            "score": 88,
            "risks": ["项目部署链路薄弱"],
            "actions": ["补充 Docker 部署练习"],
            "recentStages": ["部署追问", "技术追问"],
        },
    ]

    profile = build_candidate_profile(memories)

    assert profile["hasHistory"] is True
    assert profile["scoreTrend"] == [82, 76, 88]
    assert profile["averageScore"] == 82
    assert profile["latestScore"] == 82
    assert profile["bestScore"] == 88
    assert profile["recentRisks"] == [
        "RAG 原理解释不够清晰",
        "项目部署链路薄弱",
        "数据库设计表达薄弱",
    ]
    assert profile["frequentRisks"][:2] == ["RAG 原理解释不够清晰", "项目部署链路薄弱"]
    assert profile["frequentActions"][:2] == ["复盘 RAG 检索流程", "补充 Docker 部署练习"]
    assert profile["frequentWeakTags"] == []
    assert profile["weakStages"][:2] == ["技术追问", "项目深挖"]
    assert profile["trainingFocus"][:2] == ["复盘 RAG 检索流程", "补充 Docker 部署练习"]


def test_candidate_memory_extracts_and_aggregates_weak_tags_from_reports() -> None:
    with SessionLocal() as db:
        user = create_user(db, f"memory-tags-{uuid4().hex}@example.com")
        create_record(
            db,
            user_id=user.id,
            application_profile_id=505,
            target_role="AI 应用开发实习生",
            score=70,
            risk="RAG 质量评估薄弱",
            report_extra={
                "questionReviews": [
                    {"focus": "RAG 质量评估", "weakTags": ["rag_quality", "rag_retrieval"]},
                ],
                "trainingPlan": {
                    "weakTopics": [
                        {"focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
                    ]
                },
            },
        )
        create_record(
            db,
            user_id=user.id,
            application_profile_id=505,
            target_role="AI 应用开发实习生",
            score=78,
            risk="Agent State 表达不清",
            report_extra={
                "questionReviews": [
                    {"focus": "Agent State", "weakTags": ["agent_state", "rag_quality"]},
                ]
            },
        )

        memories = retrieve_candidate_memory(
            db,
            {
                "candidateName": "David",
                "targetRole": "AI 应用开发实习生",
                "resume": "RAG Agent",
                "jd": "RAG 质量评估 Agent State",
            },
            user_id=user.id,
            application_profile_id=505,
            limit=2,
            min_profile_records=1,
        )

    assert memories[0]["weakTags"]
    profile = build_candidate_profile(memories)
    assert profile["frequentWeakTags"][0] == "rag_quality"
    assert "agent_state" in profile["frequentWeakTags"]
    assert "高频薄弱标签：rag_quality" in format_candidate_profile(profile)


def test_format_candidate_profile_outputs_prompt_friendly_text() -> None:
    profile = {
        "hasHistory": True,
        "scoreTrend": [70, 84],
        "averageScore": 77,
        "latestScore": 70,
        "bestScore": 84,
        "recentRisks": ["回答缺少数据支撑"],
        "frequentRisks": ["RAG 原理解释不够清晰"],
        "frequentActions": ["补充项目量化指标"],
        "weakStages": ["项目深挖"],
        "trainingFocus": ["补充项目量化指标"],
    }

    text = format_candidate_profile(profile)

    assert "平均分：77" in text
    assert "分数趋势：70 -> 84" in text
    assert "高频薄弱环节：项目深挖" in text
    assert "训练重点：补充项目量化指标" in text


def test_retrieve_candidate_memory_prioritizes_current_application_profile() -> None:
    with SessionLocal() as db:
        user = create_user(db, f"memory-priority-{uuid4().hex}@example.com")
        create_record(
            db,
            user_id=user.id,
            application_profile_id=101,
            target_role="Python AI 应用实习生",
            score=72,
            risk="当前档案 RAG 解释不够具体",
        )
        create_record(
            db,
            user_id=user.id,
            application_profile_id=202,
            target_role="Python AI 应用实习生",
            score=95,
            risk="其它档案 Docker 部署薄弱",
        )

        memories = retrieve_candidate_memory(
            db,
            {
                "candidateName": "David",
                "targetRole": "Python AI 应用实习生",
                "resume": "RAG FastAPI",
                "jd": "RAG FastAPI",
            },
            user_id=user.id,
            application_profile_id=101,
            limit=2,
            min_profile_records=1,
        )

    assert memories[0]["applicationProfileId"] == 101
    assert memories[0]["risks"] == ["当前档案 RAG 解释不够具体"]


def test_retrieve_candidate_memory_falls_back_to_global_history_when_profile_history_is_sparse() -> None:
    with SessionLocal() as db:
        user = create_user(db, f"memory-fallback-{uuid4().hex}@example.com")
        create_record(
            db,
            user_id=user.id,
            application_profile_id=303,
            target_role="Python AI 应用实习生",
            score=76,
            risk="当前档案 项目指标缺失",
        )
        create_record(
            db,
            user_id=user.id,
            application_profile_id=404,
            target_role="Python AI 应用实习生",
            score=84,
            risk="全局历史 数据库迁移解释薄弱",
        )

        memories = retrieve_candidate_memory(
            db,
            {
                "candidateName": "David",
                "targetRole": "Python AI 应用实习生",
                "resume": "数据库迁移 RAG",
                "jd": "FastAPI Alembic RAG",
            },
            user_id=user.id,
            application_profile_id=303,
            limit=3,
            min_profile_records=2,
        )

    profile_ids = [memory["applicationProfileId"] for memory in memories]
    risks = [risk for memory in memories for risk in memory["risks"]]
    assert profile_ids[0] == 303
    assert 404 in profile_ids
    assert "全局历史 数据库迁移解释薄弱" in risks
