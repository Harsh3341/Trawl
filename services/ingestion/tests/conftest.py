import os, pathlib, psycopg, pytest

MIGRATION = pathlib.Path(__file__).parents[3] / "db" / "migrations" / "001_init.sql"


def dsn() -> str:
    return os.environ.get("TEST_DATABASE_URL",
                          "postgresql://trawl:trawl@localhost:5432/trawl_test")


@pytest.fixture(scope="session", autouse=True)
def _schema():
    with psycopg.connect(dsn(), autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute(MIGRATION.read_text())


@pytest.fixture()
def db():
    from app.db import Database
    database = Database.connect(dsn())
    database.truncate_all()
    return database
