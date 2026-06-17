import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend_python.auth import hash_password
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import User


@dataclass(frozen=True)
class DemoAccount:
    email: str
    username: str
    role: str
    password: str


def build_demo_accounts(*, password: str) -> list[DemoAccount]:
    return [
        DemoAccount(
            email="d77013643@gmail.com",
            username="david",
            role="user",
            password=password,
        ),
        DemoAccount(
            email="1011569954@qq.com",
            username="admin",
            role="admin",
            password=password,
        ),
    ]


def ensure_username_available(db: Session, *, username: str, email: str) -> None:
    existing = db.scalar(select(User).where(User.username == username, User.email != email))
    if existing:
        existing.username = f"{existing.username}_legacy_{existing.id}"


def upsert_demo_account(db: Session, account: DemoAccount) -> User:
    email = account.email.lower()
    ensure_username_available(db, username=account.username, email=email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            username=account.username,
            password_hash=hash_password(account.password),
            role=account.role,
        )
        db.add(user)
    else:
        user.username = account.username
        user.password_hash = hash_password(account.password)
        user.role = account.role
    db.flush()
    return user


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update local demo accounts.")
    parser.add_argument("--password", required=True, help="Password to set for all demo accounts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    init_db()
    accounts = build_demo_accounts(password=args.password)
    with SessionLocal() as db:
        users = [upsert_demo_account(db, account) for account in accounts]
        db.commit()
        for user in users:
            db.refresh(user)
            print(f"{user.email} role={user.role} username={user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
