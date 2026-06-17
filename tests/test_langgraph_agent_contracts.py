from backend_python.langgraph_agent.contracts import get_node_contracts, validate_node_trace


def test_node_contracts_include_core_workflow_nodes() -> None:
    contracts = get_node_contracts()
    names = {item["name"] for item in contracts}

    assert "observe_state" in names
    assert "retrieve_context" in names
    assert "analyze_answer" in names
    assert "apply_policy" in names
    assert "decide_action" in names
    assert "human_review" in names
    assert "generate_question" in names
    assert "update_memory" in names


def test_validate_node_trace_marks_unknown_nodes() -> None:
    result = validate_node_trace([{"node": "observe_state"}, {"node": "unknown_node"}])

    assert result["valid"] is False
    assert result["unknownNodes"] == ["unknown_node"]
    assert result["knownNodes"] == ["observe_state"]
