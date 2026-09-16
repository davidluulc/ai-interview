from backend_python.runtime_policy import decide_runtime_policy


def test_default_runtime_is_langgraph_agent_v3_for_normal_user() -> None:
    policy = decide_runtime_policy(
        requested_runtime=None,
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_agent_v3"
    assert policy["allowedRuntime"] == "langgraph_agent_v3"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph_agent_v3"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True
    assert policy["fallbackRuntime"] == "classic"
    assert "LangGraph agent v3" in policy["reasons"][0]


def test_normal_user_can_explicitly_request_langgraph_mainline_rollback() -> None:
    policy = decide_runtime_policy(
        requested_runtime="langgraph_mainline",
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_mainline"
    assert policy["allowedRuntime"] == "langgraph_mainline"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph_mainline"
    assert policy["fallbackRuntime"] == "classic"
    assert "显式回退" in policy["reasons"][0]


def test_normal_user_can_not_request_langgraph_canary() -> None:
    policy = decide_runtime_policy(
        requested_runtime="langgraph_canary",
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_canary"
    assert policy["allowedRuntime"] == "classic"
    assert policy["canUseLangGraph"] is False
    assert "普通用户暂不开放 LangGraph 灰度链路" in policy["reasons"]


def test_admin_can_request_langgraph_canary() -> None:
    policy = decide_runtime_policy(
        requested_runtime="langgraph_canary",
        user_role="admin",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_canary"
    assert policy["allowedRuntime"] == "langgraph"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True
    assert "管理员账号允许使用 LangGraph 灰度链路" in policy["reasons"]


def test_admin_shadow_still_uses_classic_as_visible_runtime() -> None:
    policy = decide_runtime_policy(
        requested_runtime="shadow",
        user_role="admin",
        agent_mode="interview",
    )

    assert policy["allowedRuntime"] == "shadow"
    assert policy["visibleRuntimeOnSuccess"] == "classic"
    assert policy["canUseLangGraph"] is True


def test_invalid_runtime_falls_back_to_langgraph_agent_v3() -> None:
    policy = decide_runtime_policy(
        requested_runtime="unknown",
        user_role="admin",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_agent_v3"
    assert policy["allowedRuntime"] == "langgraph_agent_v3"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph_agent_v3"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True
    assert "LangGraph agent v3" in policy["reasons"][0]
