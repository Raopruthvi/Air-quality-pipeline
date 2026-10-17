"""Configuration: read database settings from environment variables (.env file)."""

import os

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

load_dotenv()


def _require(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. Copy .env.example to .env and fill it in."
        )
    return value


def get_db_url():
    """Return a psycopg connection string built from the DB_* environment variables."""
    return make_conninfo(
        host=_require("DB_HOST"),
        port=_require("DB_PORT"),
        dbname=_require("DB_NAME"),
        user=_require("DB_USER"),
        password=_require("DB_PASSWORD"),
    )