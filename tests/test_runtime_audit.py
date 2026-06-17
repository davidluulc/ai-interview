from backend_python.runtime_audit import build_runtime_audit


def test_runtime_audit_records_langgraph_success() -> None:
    audit = build_runtime_audit(
        policy={
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "fallbackRuntime": "classic",
            "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
        },
        quality_gate={"passed": True, "fallbackToClassic": False, "reasons": []},
        checkpoint_summary={"exists": True, "requiresHumanReview": False},
        comparison_summary={},
        visible_runtime="langgraph",
    )

    assert audit["requestedRuntime"] == "langgraph_canary"
    assert audit["allowedRuntime"] == "langgraph"
    assert audit["visibleRuntime"] == "langgraph"
    assert audit["fallbackUsed"] is False
    assert audit["qualityGatePassed"] is True
    assert audit["checkpointExists"] is True


def test_runtime_audit_records_fallback_reasons() -> None:
    audit = build_runtime_audit(
        policy={
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "fallbackRuntime": "classic",
            "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
        },
        quality_gate={
            "passed": False,
            "fallbackToClassic": True,
            "reasons": ["LangGraph 问题与最近问题重复度过高"],
        },
        checkpoint_summary={"exists": True, "requiresHumanReview": False},
        comparison_summary={},
        visible_runtime="classic",
    )

    assert audit["visibleRuntime"] == "classic"
    assert audit["fallbackUsed"] is True
    assert audit["qualityGatePassed"] is False
    assert audit["qualityGateReasons"] == ["LangGraph 问题与最近问题重复度过高"]
