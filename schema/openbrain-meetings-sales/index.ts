#!/usr/bin/env -S deno run --allow-net --allow-env --allow-read
/**
 * OpenBrain — Meeting Notes & Sales Recordings MCP Server
 * =========================================================
 * OB1-style extension: Deno MCP tools for Claude/Cursor.
 *
 * Exposes tools:
 *   - save_meeting_note       — Insert a meeting note
 *   - save_sales_recording    — Insert a sales call recording
 *   - query_meetings           — Full-text search meetings
 *   - query_sales_recordings   — Full-text search sales recordings
 *   - get_meeting_stats        — Aggregate stats (counts by project, period)
 *   - get_sales_pipeline       — Sales call outcome distribution
 *
 * Environment:
 *   DATABASE_URL  — Postgres connection string (default: local Docker)
 *                   postgres://postgres:argus@localhost:5432/openbrain
 *
 * Usage:
 *   Claude Desktop:  add as MCP server in claude_desktop_config.json
 *   Cursor:          add in Cursor MCP settings
 *   CLI:             deno task start
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  type CallToolRequest,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import pg from 'pg';

// ─── Config ────────────────────────────────────────────────────────────

const DATABASE_URL = Deno.env.get('DATABASE_URL') ??
  'postgres://postgres:argus@localhost:5432/openbrain';

const pool = new pg.Pool({ connectionString: DATABASE_URL });

// Ollama embeddings (host-local, free). nomic-embed-text = 768 dims,
// matching vector(768) columns from openbrain-pgvector-upgrade.sql.
const OLLAMA_URL = Deno.env.get('OLLAMA_URL') ?? 'http://localhost:11434';
const EMBED_MODEL = Deno.env.get('EMBED_MODEL') ?? 'nomic-embed-text';

/** Embed text via Ollama. Returns null on any failure — callers treat
 *  embedding as best-effort so saves never fail because Ollama is down. */
async function embedText(text: string): Promise<number[] | null> {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: EMBED_MODEL, input: text.slice(0, 8000) }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const vec = data.embeddings?.[0];
    return Array.isArray(vec) && vec.length === 768 ? vec : null;
  } catch {
    return null;
  }
}

// ─── Tool definitions ──────────────────────────────────────────────────

const TOOLS = [
  {
    name: 'save_meeting_note',
    description:
      'Save a meeting note to OpenBrain. Returns the UUID of the created record.',
    inputSchema: {
      type: 'object',
      properties: {
        topic: { type: 'string', description: 'Meeting title / subject' },
        meeting_date: {
          type: 'string',
          description: 'Date of meeting (YYYY-MM-DD)',
        },
        participants: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of participant names',
        },
        duration_minutes: {
          type: 'number',
          description: 'Meeting length in minutes',
        },
        project: { type: 'string', description: 'Project name' },
        transcript_path: {
          type: 'string',
          description: 'Path to transcript file',
        },
        summary: { type: 'string', description: 'Meeting summary' },
        notes: { type: 'string', description: 'Additional notes / action items' },
        metadata: {
          type: 'object',
          description: 'Additional metadata as key-value pairs',
        },
      },
      required: ['topic', 'meeting_date'],
    },
  },
  {
    name: 'save_sales_recording',
    description:
      'Save a sales call recording reference to OpenBrain. Returns the UUID of the created record.',
    inputSchema: {
      type: 'object',
      properties: {
        prospect_name: {
          type: 'string',
          description: 'Prospect / company name',
        },
        call_date: {
          type: 'string',
          description: 'Date of call (YYYY-MM-DD)',
        },
        rep_name: { type: 'string', description: 'Sales rep name' },
        duration_seconds: {
          type: 'number',
          description: 'Call length in seconds',
        },
        audio_file_path: {
          type: 'string',
          description: 'Path to audio recording file',
        },
        transcript_path: {
          type: 'string',
          description: 'Path to call transcript',
        },
        call_outcome: {
          type: 'string',
          enum: ['booked', 'follow_up', 'no_interest', 'lost', 'other'],
          description: 'Outcome of the sales call',
        },
        notes: { type: 'string', description: 'Call summary / takeaways' },
        metadata: {
          type: 'object',
          description: 'Additional metadata as key-value pairs',
        },
      },
      required: ['prospect_name', 'call_date'],
    },
  },
  {
    name: 'query_meetings',
    description:
      'Full-text search through meeting notes. Returns matching meetings ranked by relevance.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (supports boolean operators via websearch syntax)',
        },
        limit: {
          type: 'number',
          description: 'Max results (default 20)',
          default: 20,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'query_sales_recordings',
    description:
      'Full-text search through sales call recordings. Returns matching recordings.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search prospect name or notes (ILIKE match)',
        },
        outcome: {
          type: 'string',
          enum: ['booked', 'follow_up', 'no_interest', 'lost', 'other'],
          description: 'Filter by call outcome',
        },
        limit: {
          type: 'number',
          description: 'Max results (default 20)',
          default: 20,
        },
      },
      required: [],
    },
  },
  {
    name: 'semantic_search',
    description:
      'Semantic (meaning-based) search across meeting notes and sales recordings using vector embeddings. Use this for conceptual queries like "calls where pricing anxiety came up" — falls back on nothing; requires Ollama running locally.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Natural language query — matched by meaning, not keywords',
        },
        target: {
          type: 'string',
          enum: ['meetings', 'sales', 'all'],
          description: 'Which corpus to search (default: all)',
          default: 'all',
        },
        limit: {
          type: 'number',
          description: 'Max results per corpus (default 10)',
          default: 10,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_meeting_stats',
    description:
      'Get aggregate statistics for meeting notes — total count, top projects, recent activity.',
    inputSchema: {
      type: 'object',
      properties: {
        days: {
          type: 'number',
          description: 'Lookback window in days (default 90)',
          default: 90,
        },
      },
      required: [],
    },
  },
  {
    name: 'get_sales_pipeline',
    description:
      'Get sales call recording pipeline stats — outcome distribution, total calls, top prospects.',
    inputSchema: {
      type: 'object',
      properties: {
        days: {
          type: 'number',
          description: 'Lookback window in days (default 90)',
          default: 90,
        },
      },
      required: [],
    },
  },
];

// ─── Tool handlers ─────────────────────────────────────────────────────

async function handleSaveMeetingNote(args: Record<string, unknown>) {
  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT upsert_meeting_note(
        $1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9::jsonb
      ) AS id`,
      [
        args.topic,
        args.meeting_date,
        JSON.stringify(args.participants ?? []),
        args.duration_minutes ?? null,
        args.project ?? null,
        args.transcript_path ?? null,
        args.summary ?? null,
        args.notes ?? null,
        JSON.stringify(args.metadata ?? {}),
      ],
    );
    const id = result.rows[0].id;

    // Best-effort embed-on-write (non-fatal if Ollama is down)
    const embedInput = [args.topic, args.summary, args.notes]
      .filter(Boolean).join('\n');
    const vec = await embedText(embedInput);
    if (vec) {
      await client.query(
        'UPDATE meeting_notes SET embedding = $1::vector WHERE id = $2',
        [JSON.stringify(vec), id],
      );
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          id,
          action: 'meeting_note_saved',
          embedded: vec !== null,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleSaveSalesRecording(args: Record<string, unknown>) {
  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT upsert_sales_recording(
        $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb
      ) AS id`,
      [
        args.prospect_name,
        args.call_date,
        args.rep_name ?? null,
        args.duration_seconds ?? null,
        args.audio_file_path ?? null,
        args.transcript_path ?? null,
        args.call_outcome ?? null,
        args.notes ?? null,
        JSON.stringify(args.metadata ?? {}),
      ],
    );
    const id = result.rows[0].id;

    // Best-effort embed-on-write (non-fatal if Ollama is down)
    const embedInput = [args.prospect_name, args.call_outcome, args.notes]
      .filter(Boolean).join('\n');
    const vec = await embedText(embedInput);
    if (vec) {
      await client.query(
        'UPDATE sales_recordings SET embedding = $1::vector WHERE id = $2',
        [JSON.stringify(vec), id],
      );
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          id,
          action: 'sales_recording_saved',
          embedded: vec !== null,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleQueryMeetings(args: Record<string, unknown>) {
  const query = String(args.query ?? '');
  const limit = Number(args.limit ?? 20);
  const client = await pool.connect();
  try {
    const result = await client.query(
      `SELECT id, topic, meeting_date, participants, project,
              duration_minutes, summary, notes, created_at
       FROM meeting_notes
       WHERE search_vector @@ websearch_to_tsquery('english', $1)
       ORDER BY meeting_date DESC
       LIMIT $2`,
      [query, limit],
    );

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          count: result.rows.length,
          results: result.rows,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleQuerySalesRecordings(args: Record<string, unknown>) {
  const query = String(args.query ?? '');
  const outcome = String(args.outcome ?? '');
  const limit = Number(args.limit ?? 20);
  const client = await pool.connect();
  try {
    let sql: string;
    const params: unknown[] = [];

    // Text match: indexed FTS on search_vector (prospect+rep+notes),
    // OR'd with prospect ILIKE so partial names ("Acm") still hit.
    if (outcome && query) {
      sql = `SELECT ... FROM sales_recordings
             WHERE call_outcome = $1
               AND (search_vector @@ websearch_to_tsquery('english', $2)
                    OR prospect_name ILIKE $3)
             ORDER BY call_date DESC
             LIMIT $4`;
      params.push(outcome, query, `%${query}%`, limit);
    } else if (outcome) {
      sql = `SELECT ... FROM sales_recordings
             WHERE call_outcome = $1
             ORDER BY call_date DESC LIMIT $2`;
      params.push(outcome, limit);
    } else if (query) {
      sql = `SELECT ... FROM sales_recordings
             WHERE search_vector @@ websearch_to_tsquery('english', $1)
                OR prospect_name ILIKE $2
             ORDER BY call_date DESC LIMIT $3`;
      params.push(query, `%${query}%`, limit);
    } else {
      sql = `SELECT ... FROM sales_recordings
             ORDER BY call_date DESC LIMIT $1`;
      params.push(limit);
    }

    // Build the full SELECT — reuse the column list
    const cols =
      'id, prospect_name, call_date, rep_name, duration_seconds, audio_file_path, transcript_path, call_outcome, notes, created_at';
    sql = sql.replace('...', cols);

    const result = await client.query(sql, params);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          count: result.rows.length,
          results: result.rows,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleMeetingStats(args: Record<string, unknown>) {
  const days = Number(args.days ?? 90);
  const client = await pool.connect();
  try {
    const [totalResult, projectsResult, recentResult] = await Promise.all([
      client.query('SELECT COUNT(*)::int AS total FROM meeting_notes'),
      client.query(
        `SELECT project, COUNT(*)::int AS count
         FROM meeting_notes
         WHERE meeting_date >= CURRENT_DATE - $1::interval
         GROUP BY project
         ORDER BY count DESC LIMIT 10`,
        [`${days} days`],
      ),
      client.query(
        `SELECT topic, meeting_date, project
         FROM meeting_notes
         WHERE meeting_date >= CURRENT_DATE - $1::interval
         ORDER BY meeting_date DESC LIMIT 5`,
        [`${days} days`],
      ),
    ]);

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          total_meetings: totalResult.rows[0].total,
          days_lookback: days,
          by_project: projectsResult.rows,
          recent_meetings: recentResult.rows,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleSalesPipeline(args: Record<string, unknown>) {
  const days = Number(args.days ?? 90);
  const client = await pool.connect();
  try {
    const [totalResult, outcomeResult, topProspectsResult] = await Promise.all([
      client.query('SELECT COUNT(*)::int AS total FROM sales_recordings'),
      client.query(
        `SELECT call_outcome, COUNT(*)::int AS count
         FROM sales_recordings
         WHERE call_date >= CURRENT_DATE - $1::interval
         GROUP BY call_outcome
         ORDER BY count DESC`,
        [`${days} days`],
      ),
      client.query(
        `SELECT prospect_name, COUNT(*)::int AS calls,
                MAX(call_date) AS last_call
         FROM sales_recordings
         WHERE call_date >= CURRENT_DATE - $1::interval
         GROUP BY prospect_name
         ORDER BY calls DESC LIMIT 10`,
        [`${days} days`],
      ),
    ]);

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'ok',
          total_calls: totalResult.rows[0].total,
          days_lookback: days,
          by_outcome: outcomeResult.rows,
          top_prospects: topProspectsResult.rows,
        }),
      }],
    };
  } finally {
    client.release();
  }
}

async function handleSemanticSearch(args: Record<string, unknown>) {
  const query = String(args.query ?? '');
  const target = String(args.target ?? 'all');
  const limit = Number(args.limit ?? 10);

  const vec = await embedText(query);
  if (!vec) {
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          status: 'error',
          error:
            `Embedding failed — is Ollama running at ${OLLAMA_URL} with model '${EMBED_MODEL}'? ` +
            'Semantic search requires it. Keyword tools (query_meetings, query_sales_recordings) still work.',
        }),
      }],
      isError: true,
    };
  }

  const client = await pool.connect();
  try {
    const embedding = JSON.stringify(vec);
    const out: Record<string, unknown> = { status: 'ok', query };

    if (target === 'meetings' || target === 'all') {
      const r = await client.query(
        'SELECT * FROM search_meetings_semantic($1::vector, $2)',
        [embedding, limit],
      );
      out.meetings = r.rows;
    }
    if (target === 'sales' || target === 'all') {
      const r = await client.query(
        'SELECT * FROM search_sales_semantic($1::vector, $2)',
        [embedding, limit],
      );
      out.sales = r.rows;
    }

    return {
      content: [{ type: 'text' as const, text: JSON.stringify(out) }],
    };
  } finally {
    client.release();
  }
}

// ─── Handlers map ──────────────────────────────────────────────────────

const HANDLERS: Record<string, (args: Record<string, unknown>) => ReturnType<typeof handleSaveMeetingNote>> = {
  save_meeting_note: handleSaveMeetingNote,
  save_sales_recording: handleSaveSalesRecording,
  query_meetings: handleQueryMeetings,
  query_sales_recordings: handleQuerySalesRecordings,
  semantic_search: handleSemanticSearch,
  get_meeting_stats: handleMeetingStats,
  get_sales_pipeline: handleSalesPipeline,
};

// ─── MCP Server ────────────────────────────────────────────────────────

const server = new Server(
  {
    name: 'openbrain-meetings-sales',
    version: '1.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
  const toolName = request.params.name;
  const args = request.params.arguments ?? {};

  const handler = HANDLERS[toolName];
  if (!handler) {
    return {
      content: [{ type: 'text', text: `Unknown tool: ${toolName}` }],
      isError: true,
    };
  }

  try {
    return await handler(args as Record<string, unknown>);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return {
      content: [{ type: 'text', text: JSON.stringify({ status: 'error', error: msg }) }],
      isError: true,
    };
  }
});

// ─── Start ─────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
console.error('[openbrain-meetings-sales] MCP server ready on stdio');
