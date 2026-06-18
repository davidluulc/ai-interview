from backend_python.database import build_connect_args, build_engine_options, describe_database_url, should_auto_init_db


def test_sqlite_database_url_uses_check_same_thread_false() -> None:
    assert build_connect_args("sqlite:///data/app.db") == {"check_same_thread": False}
    description = describe_database_url("sqlite:///data/app.db")
    assert description["dialect"] == "sqlite"
    assert description["isLocalSqlite"] is True
    assert description["usesExternalService"] is False


def test_postgresql_database_url_does_not_use_sqlite_connect_args() -> None:
    url = "postgresql+psycopg://user:pass@localhost:5432/app"

    assert build_connect_args(url) == {}
    options = build_engine_options(url)
    assert options["connect_args"] == {}
    assert options["pool_pre_ping"] is True
    description = describe_database_url(url)
    assert description["dialect"] == "postgresql+psycopg"
    assert description["isLocalSqlite"] is False
    assert description["usesExternalService"] is True


def test_postgresql_url_is_identified_without_exposing_password() -> None:
    result = describe_database_url(
        "postgresql+psycopg://ai_interview:super-secret@localhost:5432/ai_interview",
        auto_init=False,
    )

    assert result["dialect"] == "postgresql+psycopg"
    assert result["isPostgres"] is True
    assert result["isSqlite"] is False
    assert result["isLocalSqlite"] is False
    assert "super-secret" not in result["maskedUrl"]
    assert result["autoInitEnabled"] is False


def test_database_description_masks_password_and_marks_alembic_path() -> None:
    url = "postgresql+psycopg://app_user:secret@db:5432/interview"

    description = describe_database_url(url, auto_init=True)

    assert description["dialect"] == "postgresql+psycopg"
    assert description["isLocalSqlite"] is False
    assert description["usesExternalService"] is True
    assert description["autoInitEnabled"] is False
    assert description["migrationTool"] == "alembic"
    assert "secret" not in description["maskedUrl"]
    assert description["maskedUrl"] == "postgresql+psycopg://app_user:***@db:5432/interview"


def test_sqlite_database_description_keeps_local_path_visible() -> None:
    description = describe_database_url("sqlite:///data/app.db", auto_init=True)

    assert description["maskedUrl"] == "sqlite:///data/app.db"
    assert description["autoInitEnabled"] is True
    assert description["migrationTool"] == "metadata_create_all_for_local_sqlite"


def test_mysql_database_url_is_described_as_external_service() -> None:
    description = describe_database_url("mysql+pymysql://user:pass@localhost:3306/app")

    assert description["dialect"] == "mysql+pymysql"
    assert description["isLocalSqlite"] is False
    assert description["usesExternalService"] is True


def test_auto_init_db_defaults_to_local_sqlite_only() -> None:
    assert should_auto_init_db(auto_init=True, database_url="sqlite:///data/app.db") is True
    assert should_auto_init_db(auto_init=True, database_url="postgresql+psycopg://user:pass@db:5432/app") is False
    assert should_auto_init_db(auto_init=False, database_url="sqlite:///data/app.db") is False
