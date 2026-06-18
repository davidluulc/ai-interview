from backend_python.security import redact_error_detail


def test_redact_error_detail_removes_sensitive_values() -> None:
    message = "failed api_key=sk-secret url=sqlite:///C:/private/app.db path=C:/Users/name/project"

    redacted = redact_error_detail(message)

    assert "sk-secret" not in redacted
    assert "sqlite:///" not in redacted
    assert "C:/Users" not in redacted
