from backend_python.database import build_connect_args, build_engine_options, describe_database_url


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


def test_mysql_database_url_is_described_as_external_service() -> None:
    description = describe_database_url("mysql+pymysql://user:pass@localhost:3306/app")

    assert description["dialect"] == "mysql+pymysql"
    assert description["isLocalSqlite"] is False
    assert description["usesExternalService"] is True
