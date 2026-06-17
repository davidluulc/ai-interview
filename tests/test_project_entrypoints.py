from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_local_startup_scripts_are_explicit() -> None:
    backend = read_text("start-backend.cmd")
    frontend = read_text("start-vue-frontend.cmd")
    dev = read_text("start-dev.cmd")
    legacy = read_text("start-python-server.cmd")

    assert "backend_python.main:app" in backend
    assert "--port 8000" in backend
    assert "127.0.0.1:8000/docs" in backend
    assert "127.0.0.1:5173/vue/app/interview" in backend

    assert "cd /d \"%~dp0frontend\"" in frontend
    assert "npm.cmd run dev" in frontend
    assert "127.0.0.1:5173/vue/app/interview" in frontend

    assert "start-backend.cmd" in dev
    assert "start-vue-frontend.cmd" in dev

    assert "legacy script name" in legacy.lower()
    assert "call \"%~dp0start-backend.cmd\"" in legacy


def test_readme_explains_backend_and_vue_frontend_ports() -> None:
    readme = read_text("README.md")

    assert "当前主前端" in readme
    assert "frontend/" in readme
    assert "http://127.0.0.1:8000/docs" in readme
    assert "http://127.0.0.1:8000/api/health" in readme
    assert "http://127.0.0.1:5173/vue/app/interview" in readme
    assert "localhost:8000" in readme
    assert "旧版原生前端" in readme


def test_legacy_frontend_files_are_still_present_for_compatibility() -> None:
    assert (ROOT / "index.html").exists()
    assert (ROOT / "styles.css").exists()
    assert (ROOT / "app.js").exists()
