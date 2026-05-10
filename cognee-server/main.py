import asyncio
import json
import logging
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

# 0. Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 1. Configuration BEFORE importing Cognee
os.environ["DB_PROVIDER"] = "postgres"
os.environ["DB_HOST"] = "ob1"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "openbrain"
os.environ["DB_USERNAME"] = "postgres"
os.environ["DB_PASSWORD"] = "argus"

# LLM — DeepSeek (native provider in Cognee via PR #2790)
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["LLM_MODEL"] = "deepseek-chat"
os.environ["LLM_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")

# Embeddings — Ollama (local, free; DeepSeek has no embedding API)
os.environ["EMBEDDING_PROVIDER"] = "ollama"
os.environ["EMBEDDING_MODEL"] = os.environ.get("LOCAL_LLM_MODEL", "gemma4:e4b")
os.environ["EMBEDDING_ENDPOINT"] = "http://host.docker.internal:11434/v1"
os.environ["EMBEDDING_API_KEY"] = "dummy-key-for-ollama"
os.environ["EMBEDDING_DIMENSIONS"] = "4096"

os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"

# Data paths
os.environ["COGNEE_DATA_ROOT_DIRECTORY"] = "/app/.cognee_system"
os.environ["COGNEE_SYSTEM_ROOT_DIRECTORY"] = "/app/.cognee_system"

# 2. Import Cognee (no tiktoken patch needed — PR #2790 fixes tokenizer fallback)
import cognee

app = FastAPI(title="Argus Graph Memory (Cognee + DeepSeek)")


@app.on_event("startup")
async def init_tables():
    """Create fallback SQL query tables if Cognee's graph engine fails."""
    import psycopg2
    conn = psycopg2.connect(host="ob1", port=5432, dbname="openbrain", user="postgres", password="argus")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            description TEXT,
            type TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT nodes_name_unique UNIQUE (name)
        );
        CREATE TABLE IF NOT EXISTS edges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_node_id UUID REFERENCES nodes(id),
            target_node_id UUID REFERENCES nodes(id),
            relationship_type TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Fallback SQL tables ready.")


class LearnPayload(BaseModel):
    text: str


async def background_memorize(text: str):
    """Use Cognee's full pipeline: add → cognify → graph + embeddings."""
    try:
        logger.info("Starting Cognee add + cognify pipeline with DeepSeek...")
        await cognee.add([text])
        await cognee.cognify()
        logger.info("Cognee pipeline completed — graph stored with embeddings.")
    except Exception as e:
        logger.error(f"Cognee pipeline failed: {str(e)}", exc_info=True)
        # Fallback to direct DeepSeek extraction if Cognee fails
        logger.info("Attempting fallback extraction with DeepSeek...")
        try:
            import urllib.request
            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if key:
                graph = await asyncio.to_thread(fallback_extract, text, key)
                fallback_store(graph)
                logger.info("Fallback graph stored.")
            else:
                logger.warning("No DeepSeek key configured — skipping fallback.")
        except Exception as fe:
            logger.error(f"Fallback also failed: {str(fe)}")


def fallback_extract(text: str, api_key: str) -> dict:
    """Direct DeepSeek graph extraction as fallback."""
    import urllib.request
    prompt = f"""Extract a knowledge graph from the following text. Return ONLY valid JSON:
{{
  "entities": [{{"name": "EntityName", "type": "Person|Project|Tool|Concept|Event|Place|Organization"}}],
  "relationships": [{{"source": "EntityName", "target": "EntityName", "type": "relationship"}}]
}}
Text: {text}
JSON:"""
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Extract entities and relationships. Return ONLY valid JSON, no markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read().decode())
    content = result["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()
    return json.loads(content)


def fallback_store(graph: dict):
    """Store extracted graph in Postgres as fallback."""
    import psycopg2
    conn = psycopg2.connect(host="ob1", port=5432, dbname="openbrain", user="postgres", password="argus")
    cur = conn.cursor()
    try:
        for e in graph.get("entities", []):
            cur.execute(
                "INSERT INTO nodes (id, name, description, type, created_at) VALUES (gen_random_uuid(), %s, %s, %s, NOW()) ON CONFLICT (name) DO NOTHING",
                (e["name"], e.get("description", e["name"]), e.get("type", "Concept")),
            )
        for r in graph.get("relationships", []):
            cur.execute(
                """INSERT INTO edges (id, source_node_id, target_node_id, relationship_type, created_at)
                   SELECT gen_random_uuid(), n1.id, n2.id, %s, NOW()
                   FROM nodes n1, nodes n2 WHERE n1.name = %s AND n2.name = %s""",
                (r["type"], r["source"], r["target"]),
            )
        conn.commit()
        logger.info(f"Fallback: stored {len(graph.get('entities', []))} nodes, {len(graph.get('relationships', []))} edges.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Fallback DB write error: {e}")
    finally:
        cur.close()
        conn.close()


def query_graph_db(q: str) -> list:
    """Fallback SQL search on nodes/edges. Tokenizes query for multi-word matching."""
    import psycopg2
    conn = psycopg2.connect(host="ob1", port=5432, dbname="openbrain", user="postgres", password="argus")
    cur = conn.cursor()
    try:
        tokens = [t for t in q.split() if len(t) > 2]
        if not tokens:
            tokens = [q]
        clauses = " OR ".join(["n.name ILIKE %s OR n.description ILIKE %s"] * len(tokens))
        params = []
        for t in tokens:
            params.extend([f"%{t}%", f"%{t}%"])
        cur.execute(
            f"SELECT n.name, n.description, n.type FROM nodes n WHERE {clauses} LIMIT 20",
            params,
        )
        nodes = [{"name": r[0], "description": r[1], "type": r[2]} for r in cur.fetchall()]
        results = []
        for node in nodes:
            cur.execute(
                "SELECT e.relationship_type, n2.name FROM edges e JOIN nodes n2 ON e.target_node_id = n2.id WHERE e.source_node_id = (SELECT id FROM nodes WHERE name = %s LIMIT 1) LIMIT 10",
                (node["name"],),
            )
            relations = [{"type": r[0], "target": r[1]} for r in cur.fetchall()]
            results.append({**node, "relations": relations} if relations else node)
        return results
    finally:
        cur.close()
        conn.close()


@app.post("/learn", status_code=202)
async def learn_graph(payload: LearnPayload, background_tasks: BackgroundTasks):
    logger.info("Received /learn request. Queuing Cognee pipeline.")
    background_tasks.add_task(background_memorize, payload.text)
    return {"status": "queued", "message": "Memory extraction running in background."}


@app.get("/query")
async def query_graph(q: str):
    try:
        logger.info(f"Querying graph for: {q}")
        # Try Cognee's semantic search first
        try:
            results = await cognee.search(q)
            if results:
                return {"status": "success", "engine": "cognee", "data": [str(r) for r in results[:10]]}
        except Exception as ce:
            logger.warning(f"Cognee search failed, falling back to SQL: {ce}")

        # Fallback to SQL
        sql_results = query_graph_db(q)
        return {"status": "success", "engine": "sql_fallback", "data": sql_results}
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
