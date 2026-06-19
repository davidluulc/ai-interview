import json

from backend_python.database import SessionLocal
from backend_python.db_models import User
from backend_python.production_rag_seed import run_production_rag_seed


def get_seed_owner(db) -> User:
    user = db.query(User).filter(User.role == "admin").order_by(User.id.asc()).first()
    if user:
        return user

    user = db.query(User).filter(User.username == "production_seed").first()
    if user:
        return user

    user = User(
        email="production-seed@example.local",
        username="production_seed",
        password_hash="disabled",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    with SessionLocal() as db:
        user = get_seed_owner(db)
        summary = run_production_rag_seed(db, user_id=user.id)
        print(json.dumps({"userId": user.id, **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
