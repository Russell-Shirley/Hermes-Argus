"""MCP stdio server wrapping Cognee graph memory REST API.

Exposes cognee__memorize and cognee__query as MCP tools via stdin/stdout JSON-RPC.
"""
import json
import httpx
from mcp.server.fastmcp import FastMCP

COGNEE_URL = "http://localhost:8000"

mcp = FastMCP("cognee-graph-memory")


@mcp.tool(
    name="cognee__memorize",
    description="Store a factual statement in the knowledge graph for long-term relational memory. Use this for facts about people, companies, projects, preferences, and relationships.",
)
async def cognee_memorize(text: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{COGNEE_URL}/learn",
            json={"text": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)


@mcp.tool(
    name="cognee__query",
    description="Search the knowledge graph for entities, relationships, and facts. Use this when asked 'what do you know about X' or when you need to recall stored information.",
)
async def cognee_query(query: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{COGNEE_URL}/query",
            params={"q": query},
        )
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)


if __name__ == "__main__":
    mcp.run(transport="stdio")
