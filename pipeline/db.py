import os
import psycopg

DEFAULT_DSN = "postgresql://qa:qa@localhost:5433/ingest"


def dsn() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DSN)


def connect():
    return psycopg.connect(dsn(), autocommit=False)
