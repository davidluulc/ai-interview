from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def load_compose() -> dict:
    return yaml.safe_load(read_text("docker-compose.yml"))


def test_production_env_template_uses_placeholders_only() -> None:
    path = ROOT_DIR / ".env.production.example"

    assert path.exists()
    content = path.read_text(encoding="utf-8")

    assert "DASHSCOPE_API_KEY=replace_with_dashscope_api_key" in content
    assert "EMBEDDING_PROVIDER=dashscope" in content
    assert "EMBEDDING_API_KEY=" in content
    assert "EMBEDDING_MODEL=text-embedding-v4" in content
    assert "EMBEDDING_REQUIRE_MODEL_MATCH=true" in content
    assert "SECRET_KEY=replace_with_long_random_secret" in content
    assert "DATABASE_URL=postgresql+psycopg://" in content
    assert "AUTO_INIT_DB=false" in content
    assert "REDIS_ENABLED=true" in content
    assert "CELERY_TASK_ALWAYS_EAGER=false" in content
    assert "sk-" not in content
    assert "kwb1515yxq" not in content


def test_dockerignore_excludes_local_state_and_secrets() -> None:
    content = read_text(".dockerignore")

    required_patterns = [
        ".env",
        ".env.*",
        "!*.example",
        "data/*.db",
        "__pycache__/",
        ".pytest_cache/",
        ".idea/",
        "*.log",
        "node_modules/",
    ]
    for pattern in required_patterns:
        assert pattern in content


def test_dockerfile_builds_fastapi_app() -> None:
    content = read_text("Dockerfile")

    assert "FROM python:" in content
    assert "COPY requirements.txt" in content
    assert "pip install" in content
    assert "EXPOSE 8000" in content
    assert "backend_python.main:app" in content
    assert "--host" in content
    assert "0.0.0.0" in content


def test_compose_defines_deployment_services() -> None:
    content = read_text("docker-compose.yml")

    for service in ["app:", "db:", "redis:", "worker:", "nginx:"]:
        assert service in content
    assert "image: ai-interview-app:local" in content
    for env_name in [
        "DASHSCOPE_API_KEY",
        "QWEN_MODEL",
        "QWEN_VISION_MODEL",
        "DASHSCOPE_EMBEDDING_MODEL",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_API_KEY",
        "EMBEDDING_MODEL",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_DIMENSIONS",
        "EMBEDDING_REQUIRE_MODEL_MATCH",
        "DASHSCOPE_RERANK_MODEL",
        "SECRET_KEY",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "AUTO_INIT_DB",
    ]:
        assert env_name in content
    assert "postgres:16" in content
    assert "redis:7" in content
    assert "CELERY_TASK_ALWAYS_EAGER" in content
    assert "false" in content
    assert "deploy/nginx/ai-interview.conf" in content
    assert "5432" in content
    assert "6379" in content


def test_compose_contains_app_worker_db_redis_nginx_services() -> None:
    compose = load_compose()

    assert {"app", "worker", "db", "redis", "nginx"}.issubset(set(compose["services"]))


def test_compose_sets_stable_project_name_for_non_ascii_workspace_path() -> None:
    compose = load_compose()

    assert compose["name"] == "ai-interview"


def test_worker_uses_same_image_and_celery_command() -> None:
    compose = load_compose()
    app = compose["services"]["app"]
    worker = compose["services"]["worker"]

    assert worker["image"] == app["image"]
    assert "celery" in worker["command"]
    assert "backend_python.celery_app.celery_app" in worker["command"]
    assert worker["environment"]["CELERY_TASK_ALWAYS_EAGER"] == "${CELERY_TASK_ALWAYS_EAGER:-false}"


def test_nginx_mounts_project_reverse_proxy_config() -> None:
    compose = load_compose()
    nginx = compose["services"]["nginx"]

    assert any("deploy/nginx/ai-interview.conf" in volume for volume in nginx["volumes"])
    assert any("frontend/dist:/usr/share/nginx/html/vue:ro" in volume for volume in nginx["volumes"])
    assert "8080:80" in nginx["ports"]


def test_nginx_config_proxies_frontend_api_and_docs() -> None:
    content = read_text("deploy/nginx/ai-interview.conf")

    assert "upstream ai_interview_app" in content
    assert "server app:8000" in content
    assert "return 302 /vue/auth/login" in content
    assert "location /vue/" in content
    assert "try_files $uri $uri/ /vue/index.html" in content
    assert "location /api/" in content
    assert "location /docs" in content
    assert "location /openapi.json" in content
    assert "proxy_set_header Host $host" in content
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for" in content
    assert "proxy_read_timeout" in content
