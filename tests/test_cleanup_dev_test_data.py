from types import SimpleNamespace

from scripts.cleanup_dev_test_data import DEFAULT_KEEP_EMAILS, is_test_user


def user(email: str, username: str = "user") -> SimpleNamespace:
    return SimpleNamespace(email=email, username=username)


def test_is_test_user_matches_generated_test_accounts() -> None:
    assert is_test_user(user("summary-admin-abc@example.com", "summary_admin_abc")) is True
    assert is_test_user(user("codex.ui.test.20260612@gmail.com", "codex_ui_1234")) is True
    assert is_test_user(user("rag-quality-admin-abc@example.com", "rag_quality_admin_abc")) is True


def test_is_test_user_protects_real_demo_accounts() -> None:
    assert "d77013643@gmail.com" in DEFAULT_KEEP_EMAILS
    assert "1011569954@qq.com" in DEFAULT_KEEP_EMAILS
    assert is_test_user(user("d77013643@gmail.com", "david")) is False
    assert is_test_user(user("1011569954@qq.com", "admin")) is False


def test_is_test_user_can_include_explicit_legacy_demo_email() -> None:
    assert is_test_user(user("admin@ai-interview.com", "admin"), include_emails={"admin@ai-interview.com"}) is True
    assert is_test_user(user("demo@ai-interview.com", "demo"), include_emails={"demo@ai-interview.com"}) is True
