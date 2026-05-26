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

# LLM — env-driven via .env.llm.active (deepseek default, gemma toggle via switch-llm.ps1)
# setdefault so .env values win; hardcoded values are fallbacks only.
os.environ.setdefault("LLM_PROVIDER", "deepseek")
os.environ.setdefault("LLM_MODEL", "deepseek-chat")
if not os.environ.get("LLM_API_KEY"):
    os.environ["LLM_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")

# Embeddings — env-driven; default nomic-embed-text (768 dim, purpose-built embedder)
os.environ.setdefault("EMBEDDING_PROVIDER", "ollama")
os.environ.setdefault("EMBEDDING_MODEL", "nomic-embed-text")
os.environ.setdefault("EMBEDDING_ENDPOINT", "http://host.docker.internal:11434/api/embed")
os.environ.setdefault("EMBEDDING_API_KEY", "dummy-key-for-ollama")
os.environ.setdefault("EMBEDDING_DIMENSIONS", "768")

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
    """Fallback SQL search — reads Cognee v1 data table + file contents.
    Cognee v1 uses hash-based filenames (not searchable by name ILIKE),
    so we scan recent files for keyword matches."""
    import psycopg2
    import os
    conn = psycopg2.connect(host="ob1", port=5432, dbname="openbrain", user="postgres", password="argus")
    cur = conn.cursor()
    try:
        tokens = [t.lower() for t in q.split() if len(t) > 2]
        if not tokens:
            tokens = [q.lower()]

        # Get all records, scan file contents for keyword matches
        cur.execute('SELECT id, name, raw_data_location FROM "data" ORDER BY created_at DESC LIMIT 50')
        rows = cur.fetchall()

        results = []
        for row_id, name, raw_loc in rows:
            content = None
            matched = False
            if raw_loc and raw_loc.startswith("file://"):
                fp = raw_loc[7:]
                try:
                    with open(fp) as f:
                        content = f.read(2000)
                    # Check if any token matches in content
                    content_lower = content.lower()
                    matched = any(t in content_lower for t in tokens)
                except (FileNotFoundError, IOError):
                    content = None

            # Also match by name
            if not matched and name:
                name_lower = name.lower()
                matched = any(t in name_lower for t in tokens)

            if not matched:
                continue

            # Look up edges
            try:
                cur.execute(
                    'SELECT e.relationship_type, eo.name FROM "edges" e '
                    'JOIN "data" eo ON e.target_node_id = eo.id '
                    'WHERE e.source_node_id = %s LIMIT 10',
                    (row_id,),
                )
                relations = [{"type": r[0], "target": r[1]} for r in cur.fetchall()]
            except Exception:
                relations = []

            entry = {"name": name, "content": content[:500] if content else None}
            if relations:
                entry["relations"] = relations
            results.append(entry)

            if len(results) >= 10:
                break

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
        # Skip cognee.search — it blocks the event loop calling Gemma3 via Ollama
        # on Windows (unreachable from Docker). Go straight to SQL fallback.
        logger.info("Skipping cognee.search (Ollama unreachable from Docker), using SQL fallback")
        sql_results = query_graph_db(q)
        return {"status": "success", "engine": "sql_fallback", "data": sql_results}
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
