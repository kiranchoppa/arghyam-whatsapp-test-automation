"""Database connection and generic query execution.

This module is responsible only for:
- Opening / closing psycopg2 connections.
- Executing a query and returning raw rows.

All SQL strings and business logic live elsewhere (queries.py / services/).
"""

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection(db_url, db_username, db_password):
    """Return an open psycopg2 connection.

    Accepts both libpq-style URLs (postgresql://...) and JDBC-style URLs
    (jdbc:postgresql://...); the jdbc: prefix is stripped automatically.
    The caller is responsible for closing the connection.
    """
    if db_url.startswith("jdbc:"):
        db_url = db_url[len("jdbc:"):]
    return psycopg2.connect(db_url, user=db_username, password=db_password)


def execute_query(conn, query, params=None):
    """Execute query with params and return all rows as a list of dicts.

    The connection is NOT closed here; the caller manages its lifecycle.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params or {})
        rows = cur.fetchall()
    return [dict(row) for row in rows]
