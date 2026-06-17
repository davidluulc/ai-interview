from backend_python.langgraph_agent.runtime_report import build_runtime_report


def test_runtime_report_returns_safe_empty_report() -> None:
    report = build_runtime_report("thread-empty", [])

    assert report["threadId"] == "thread-empty"
    assert report["totalRuns"] == 0
    assert report["statusCounts"] == {}
    assert report["fallbackCount"] == 0
    assert report["humanReviewCount"] == 0
    assert report["topQualityGateReasons"] == []
    assert report["summary"] == "暂无 LangGraph runtime 运行记录。"


def test_runtime_report_aggregates_status_fallback_and_quality_reasons() -> None:
    report = build_runtime_report(
        "thread-a",
        [
            {
                "status": "completed",
                "requiresHumanReview": False,
                "runtimeAudit": {
                    "fallbackUsed": True,
                    "qualityGateReasons": ["问题为空", "问题为空"],
                },
                "qualityGate": {"reasons": ["缺少 checkpoint"]},
            },
            {
                "status": "interrupted",
                "requiresHumanReview": True,
                "runtimeAudit": {"fallbackUsed": False, "qualityGateReasons": ["需要人工复核"]},
            },
            {
                "status": "failed",
                "interrupt": {"reason": "连续弱回答"},
                "runtimeAudit": {"fallbackUsed": True, "qualityGateReasons": ["问题为空"]},
            },
        ],
    )

    assert report["threadId"] == "thread-a"
    assert report["totalRuns"] == 3
    assert report["statusCounts"] == {"completed": 1, "interrupted": 1, "failed": 1}
    assert report["fallbackCount"] == 2
    assert report["humanReviewCount"] == 2
    assert report["topQualityGateReasons"][0] == {"reason": "问题为空", "count": 3}
    assert {"reason": "缺少 checkpoint", "count": 1} in report["topQualityGateReasons"]
    assert report["summary"] == "该线程共 3 次运行，其中 2 次 fallback、2 次触发人工复核，需要继续观察。"
