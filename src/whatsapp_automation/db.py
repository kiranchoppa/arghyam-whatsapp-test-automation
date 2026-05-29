"""Database connection and query execution.

Responsible only for:
- Opening a psycopg2 connection from env vars.
- Executing a query and returning raw rows.

All SQL strings live in the service files under services/.
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


def get_connection():
    """Return an open psycopg2 connection using env vars.

    Accepts both postgres:// and jdbc:postgresql:// style URLs.
    The caller is responsible for closing the connection.
    """
    load_dotenv()
    db_url = os.getenv("DB_URL", "").strip()
    db_username = os.getenv("DB_USERNAME", "").strip()
    db_password = os.getenv("DB_PASSWORD", "").strip()

    if not db_url:
        raise ValueError("Missing DB_URL in .env")

    if db_url.startswith("jdbc:"):
        db_url = db_url[len("jdbc:"):]

    return psycopg2.connect(db_url, user=db_username, password=db_password)


def execute_query(conn, query, params=None):
    """Execute a query and return all rows as a list of dicts.

    The connection is NOT closed here; the caller manages its lifecycle.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params or {})
        rows = cur.fetchall()
    return [dict(row) for row in rows]
