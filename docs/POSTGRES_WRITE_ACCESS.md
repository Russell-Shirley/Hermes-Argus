# PostgreSQL MCP Write Access — Resolved

## Problem

The `@modelcontextprotocol/server-postgres` MCP server only registers a read-only `query` tool, preventing all INSERT/UPDATE/DELETE operations needed by cron jobs.

## Root Cause

The npm package (`@modelcontextprotocol/server-postgres` v0.6.2) is hardcoded to execute all queries within READ ONLY transactions. There is no configuration flag to enable writes. The package is also deprecated.

## Solution

Replaced the npm package with a custom Python MCP wrapper:

**File:** `cognee-server/postgres_mcp.py`

A Python stdio MCP server using `FastMCP` and `psycopg2` that exposes two tools:

| Tool | Purpose | Returns |
|------|---------|---------|
| `query` | Read-only SELECT queries | JSON array of rows |
| `execute` | Write statements (INSERT/UPDATE/DELETE) | `{"affected_rows": N}` |

### Files Changed

| File | Change |
|------|--------|
| `cognee-server/postgres_mcp.py` | **New** — Python MCP wrapper with read + write |
| `~/.hermes/config.yaml` | MCP server `command` → `python postgres_mcp.py` |
| `~/.hermes/profiles/*/config.yaml` | Same update across all 3 profiles |
| `config/hermes.yaml` | Source template updated |

### Config Before

```yaml
postgres:
  command: npx
  args:
  - -y
  - '@modelcontextprotocol/server-postgres'
  - ${POSTGRES_CONNECTION_STRING}
  tools:
    include:
    - query
    - execute    # ← never registered by the server
```

### Config After

```yaml
postgres:
  command: C:\Users\Russell\AppData\Local\Python\pythoncore-3.14-64\python.exe
  args: ["C:\\Users\\Russell\\Documents\\GitHub\\Hermes-Argus\\cognee-server\\postgres_mcp.py"]
```

The `POSTGRES_CONNECTION_STRING` is read from the environment at runtime (no need to pass as arg).

## Architecture

- `POSTGRES_CONNECTION_STRING` is read from `os.environ` at call time
- Each tool call opens a fresh connection + autocommits via `with conn:`
- DDL statements return `affected_rows: -1` (psycopg2 convention)
- No `tools.include` filter needed — only `query` and `execute` are registered

## Verification

Gateway log confirms successful registration:
```
MCP server 'postgres' (stdio): registered 6 tool(s):
  mcp_postgres_query,
  mcp_postgres_execute,
  mcp_postgres_list_resources,
  mcp_postgres_read_resource,
  mcp_postgres_list_prompts,
  mcp_postgres_get_prompt
```

### Validation

Run manually:
```sql
INSERT INTO voucher_queue (filename, status) VALUES ('test_vendor_invoice.pdf', 'pending');
```

Then trigger the cron:
```powershell
& $hermesExe cron tick
```

## Dependencies

- Python 3.14+ with `psycopg2-binary` (already in `cognee-server/requirements.txt`)
- `mcp` package (Python MCP SDK, already installed for `cognee-server/mcp_wrapper.py`)
