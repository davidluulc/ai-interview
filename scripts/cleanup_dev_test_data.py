import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend_python.database import SessionLocal, init_db
from backend_python.db_models import (
    AgentDecisionLog,
    ApplicationProfile,
    InterviewRecord,
    RagChunk,
    RagDocument,
    RagRetrievalLog,
    RefreshToken,
    TrainingTask,
    User,
)

DEFAULT_KEEP_EMAILS = {
    "d77013643@gmail.com",
    "1011569954@qq.com",
}

TEST_EMAIL_PREFIXES = (
    "admin-dep-",
    "admin-list-",
    "codex.",
    "codex_",
    "history-",
    "rag-quality-",
    "role-admin-",
    "role-user-",
    "student-",
    "summary-admin-",
    "summary-user-",
    "training-user-",
)

TEST_USERNAME_PREFIXES = (
    "admin_dep_",
    "admin_list_",
    "codex_",
    "history_",
    "rag_quality_",
    "role_admin_",
    "role_user_",
    "student_",
    "summary_admin_",
    "summary_user_",
    "training_user_",
)


@dataclass(frozen=True)
class CleanupPreview:
    user_ids: list[int]
    user_count: int
    refresh_token_count: int
    profile_count: int
    interview_count: int
    rag_document_count: int
    rag_chunk_count: int
    rag_log_count: int
    agent_log_count: int
    training_task_count: int


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def is_test_user(
    user: User,
    keep_emails: set[str] | None = None,
    include_emails: set[str] | None = None,
) -> bool:
    keep = {normalize_email(email) for email in (keep_emails or DEFAULT_KEEP_EMAILS)}
    include = {normalize_email(email) for email in (include_emails or set())}
    email = normalize_email(user.email)
    username = str(user.username or "").strip().lower()
    if email in include:
        return True
    if email in keep:
        return False
    if email.endswith("@example.com"):
        return True
    if any(email.startswith(prefix) for prefix in TEST_EMAIL_PREFIXES):
        return True
    return any(username.startswith(prefix) for prefix in TEST_USERNAME_PREFIXES)


def find_test_user_ids(
    db: Session,
    keep_emails: set[str] | None = None,
    include_emails: set[str] | None = None,
) -> list[int]:
    users = db.scalars(select(User)).all()
    return [user.id for user in users if is_test_user(user, keep_emails=keep_emails, include_emails=include_emails)]


def count_model(db: Session, model: type, user_ids: list[int]) -> int:
    if not user_ids:
        return 0
    return int(db.scalar(select(func.count()).select_from(model).where(model.user_id.in_(user_ids))) or 0)


def build_preview(
    db: Session,
    keep_emails: set[str] | None = None,
    include_emails: set[str] | None = None,
) -> CleanupPreview:
    user_ids = find_test_user_ids(db, keep_emails=keep_emails, include_emails=include_emails)
    return CleanupPreview(
        user_ids=user_ids,
        user_count=len(user_ids),
        refresh_token_count=count_model(db, RefreshToken, user_ids),
        profile_count=count_model(db, ApplicationProfile, user_ids),
        interview_count=count_model(db, InterviewRecord, user_ids),
        rag_document_count=count_model(db, RagDocument, user_ids),
        rag_chunk_count=count_model(db, RagChunk, user_ids),
        rag_log_count=count_model(db, RagRetrievalLog, user_ids),
        agent_log_count=count_model(db, AgentDecisionLog, user_ids),
        training_task_count=count_model(db, TrainingTask, user_ids),
    )


def delete_test_data(db: Session, user_ids: list[int]) -> None:
    if not user_ids:
        return
    for model in (
        RefreshToken,
        TrainingTask,
        RagChunk,
        RagDocument,
        RagRetrievalLog,
        AgentDecisionLog,
        InterviewRecord,
        ApplicationProfile,
    ):
        db.execute(delete(model).where(model.user_id.in_(user_ids)))
    db.execute(delete(User).where(User.id.in_(user_ids)))


def format_preview(preview: CleanupPreview, *, apply: bool) -> str:
    mode = "APPLY" if apply else "DRY-RUN"
    lines = [
        f"Mode: {mode}",
        f"Matched test users: {preview.user_count}",
        f"Refresh tokens: {preview.refresh_token_count}",
        f"Application profiles: {preview.profile_count}",
        f"Interview records: {preview.interview_count}",
        f"RAG documents: {preview.rag_document_count}",
        f"RAG chunks: {preview.rag_chunk_count}",
        f"RAG retrieval logs: {preview.rag_log_count}",
        f"Agent decision logs: {preview.agent_log_count}",
        f"Training tasks: {preview.training_task_count}",
    ]
    if not apply:
        lines.append("No data was deleted. Re-run with --apply to delete matched test data.")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or clean generated local development test data.")
    parser.add_argument("--apply", action="store_true", help="Actually delete matched test data. Omit for dry-run.")
    parser.add_argument(
        "--keep-email",
        action="append",
        default=[],
        help="Email to protect from cleanup. Can be passed multiple times.",
    )
    parser.add_argument(
        "--include-email",
        action="append",
        default=[],
        help="Email to explicitly include in cleanup. Can be passed multiple times.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    keep_emails = DEFAULT_KEEP_EMAILS | {normalize_email(email) for email in args.keep_email}
    include_emails = {normalize_email(email) for email in args.include_email}
    init_db()
    with SessionLocal() as db:
        preview = build_preview(db, keep_emails=keep_emails, include_emails=include_emails)
        if args.apply:
            delete_test_data(db, preview.user_ids)
            db.commit()
        print(format_preview(preview, apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
