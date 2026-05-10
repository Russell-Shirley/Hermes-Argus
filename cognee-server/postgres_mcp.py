"""MCP stdio server wrapping PostgreSQL with read + write access.

Exposes query (SELECT) and execute (INSERT/UPDATE/DELETE) as MCP tools
via stdin/stdout JSON-RPC. Replaces the read-only @modelcontextprotocol/server-postgres.
"""
import json
import os
import psycopg2
from psycopg2 import sql as psql
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("postgres")

CONNECTION_STRING = os.environ.get("POSTGRES_CONNECTION_STRING", "")


def get_conn():
    return psycopg2.connect(CONNECTION_STRING)


@mcp.tool(
    name="query",
    description="Execute a read-only SQL SELECT query against PostgreSQL. Returns rows as a JSON array. For INSERT/UPDATE/DELETE use the execute tool.",
)
def query(sql: str) -> str:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(psql.SQL(sql))
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description] if cur.description else []
                result = [dict(zip(colnames, row)) for row in rows]
                return json.dumps(result, default=str)
    finally:
        conn.close()


@mcp.tool(
    name="execute",
    description="Execute a write SQL statement (INSERT, UPDATE, DELETE) against PostgreSQL. Returns the number of affected rows. For SELECT queries use the query tool.",
)
def execute(sql: str) -> str:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(psql.SQL(sql))
                rowcount = cur.rowcount
                return json.dumps({"affected_rows": rowcount})
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")
