from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python import auth
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()


def promote_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()


def test_registered_user_defaults_to_user_role() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    result = register_and_login(client, f"role-user-{suffix}@example.com", f"role_user_{suffix[:8]}")

    assert result["user"]["role"] == "user"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {result['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"


def test_admin_role_is_returned_after_login() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"role-admin-{suffix}@example.com"
    username = f"role_admin_{suffix[:8]}"
    register_and_login(client, email, username)
    promote_to_admin(email)

    result = client.post("/api/auth/login", json={"email": email, "password": "password123"})

    assert result.status_code == 200
    assert result.json()["user"]["role"] == "admin"


def test_require_admin_user_allows_admin_and_rejects_user() -> None:
    require_admin_user = getattr(auth, "require_admin_user", None)
    assert callable(require_admin_user)

    local_app = FastAPI()

    @local_app.get("/admin-only")
    async def admin_only(_: User = Depends(require_admin_user)) -> dict[str, bool]:
        return {"ok": True}

    init_db()
    client = TestClient(local_app)
    app_client = TestClient(app)

    suffix = uuid4().hex
    user_email = f"admin-dep-user-{suffix}@example.com"
    admin_email = f"admin-dep-admin-{suffix}@example.com"
    user = register_and_login(app_client, user_email, f"admin_dep_user_{suffix[:8]}")
    register_and_login(app_client, admin_email, f"admin_dep_admin_{suffix[:8]}")
    promote_to_admin(admin_email)
    admin = app_client.post("/api/auth/login", json={"email": admin_email, "password": "password123"}).json()

    no_token = client.get("/admin-only")
    user_response = client.get("/admin-only", headers={"Authorization": f"Bearer {user['accessToken']}"})
    admin_response = client.get("/admin-only", headers={"Authorization": f"Bearer {admin['accessToken']}"})

    assert no_token.status_code == 401
    assert user_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.json() == {"ok": True}
