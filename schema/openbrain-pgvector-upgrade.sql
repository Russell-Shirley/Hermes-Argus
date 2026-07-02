-- ============================================================
-- Open Brain: pgvector upgrade + review fixes
-- ============================================================
-- Adds semantic search (pgvector/HNSW), fixes from OB1 review:
--   #1 semantic layer  #2 real upserts  #3 generated FTS  #4 view join
-- REQUIRES: pgvector/pgvector:pg17 image (docker-compose.yml)
-- Apply: docker exec -i argus-openbrain psql -U postgres -d openbrain ^
--          < schema/openbrain-pgvector-upgrade.sql
-- Cognee tables are NOT touched by this migration.
-- ============================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1) EMBEDDING COLUMNS (nomic-embed-text = 768 dims) + HNSW
-- ============================================================

ALTER TABLE meeting_notes
  ADD COLUMN IF NOT EXISTS embedding vector(768);
ALTER TABLE sales_recordings
  ADD COLUMN IF NOT EXISTS embedding vector(768);

CREATE INDEX IF NOT EXISTS idx_meeting_notes_embedding
  ON meeting_notes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_sales_recordings_embedding
  ON sales_recordings USING hnsw (embedding vector_cosine_ops);

-- ============================================================
-- 2) GENERATED FTS COLUMNS (fix: old GIN index on topic-only
--    never matched the query expression -> seq scans)
-- ============================================================

ALTER TABLE meeting_notes
  ADD COLUMN IF NOT EXISTS search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(topic,'') || ' ' || coalesce(summary,'') || ' ' ||
      coalesce(notes,'') || ' ' || coalesce(project,''))
  ) STORED;

ALTER TABLE sales_recordings
  ADD COLUMN IF NOT EXISTS search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(prospect_name,'') || ' ' || coalesce(rep_name,'') || ' ' ||
      coalesce(notes,''))
  ) STORED;

DROP INDEX IF EXISTS idx_meeting_notes_topic;
CREATE INDEX IF NOT EXISTS idx_meeting_notes_search
  ON meeting_notes USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_sales_recordings_search
  ON sales_recordings USING gin(search_vector);

-- ============================================================
-- 3) IDEMPOTENCY: natural keys + real upserts
--    (fix: old "upsert" functions were insert-only -> dupes
--    under agent retries / transcript reprocessing)
--    Natural keys: (topic, meeting_date) / (prospect_name, call_date).
--    Tradeoff: a 2nd same-day call w/ same prospect UPDATES the row;
--    differentiate via distinct topic or transcript_path if needed.
-- ============================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_meeting_notes_topic_date
  ON meeting_notes (topic, meeting_date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_recordings_prospect_date
  ON sales_recordings (prospect_name, call_date);

CREATE OR REPLACE FUNCTION upsert_meeting_note(
  p_topic TEXT,
  p_meeting_date DATE,
  p_participants JSONB DEFAULT '[]'::jsonb,
  p_duration_minutes INTEGER DEFAULT NULL,
  p_project TEXT DEFAULT NULL,
  p_transcript_path TEXT DEFAULT NULL,
  p_summary TEXT DEFAULT NULL,
  p_notes TEXT DEFAULT NULL,
  p_external_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
  v_id UUID;
BEGIN
  INSERT INTO meeting_notes (topic, meeting_date, participants,
    duration_minutes, project, transcript_path, summary, notes,
    external_metadata)
  VALUES (p_topic, p_meeting_date, p_participants, p_duration_minutes,
    p_project, p_transcript_path, p_summary, p_notes, p_external_metadata)
  ON CONFLICT (topic, meeting_date) DO UPDATE SET
    participants      = EXCLUDED.participants,
    duration_minutes  = COALESCE(EXCLUDED.duration_minutes, meeting_notes.duration_minutes),
    project           = COALESCE(EXCLUDED.project, meeting_notes.project),
    transcript_path   = COALESCE(EXCLUDED.transcript_path, meeting_notes.transcript_path),
    summary           = COALESCE(EXCLUDED.summary, meeting_notes.summary),
    notes             = COALESCE(EXCLUDED.notes, meeting_notes.notes),
    external_metadata = meeting_notes.external_metadata || EXCLUDED.external_metadata,
    updated_at        = NOW()
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION upsert_sales_recording(
  p_prospect_name TEXT,
  p_call_date DATE,
  p_rep_name TEXT DEFAULT NULL,
  p_duration_seconds INTEGER DEFAULT NULL,
  p_audio_file_path TEXT DEFAULT NULL,
  p_transcript_path TEXT DEFAULT NULL,
  p_call_outcome TEXT DEFAULT NULL,
  p_notes TEXT DEFAULT NULL,
  p_external_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
  v_id UUID;
BEGIN
  INSERT INTO sales_recordings (prospect_name, call_date, rep_name,
    duration_seconds, audio_file_path, transcript_path, call_outcome,
    notes, external_metadata)
  VALUES (p_prospect_name, p_call_date, p_rep_name, p_duration_seconds,
    p_audio_file_path, p_transcript_path, p_call_outcome, p_notes,
    p_external_metadata)
  ON CONFLICT (prospect_name, call_date) DO UPDATE SET
    rep_name          = COALESCE(EXCLUDED.rep_name, sales_recordings.rep_name),
    duration_seconds  = COALESCE(EXCLUDED.duration_seconds, sales_recordings.duration_seconds),
    audio_file_path   = COALESCE(EXCLUDED.audio_file_path, sales_recordings.audio_file_path),
    transcript_path   = COALESCE(EXCLUDED.transcript_path, sales_recordings.transcript_path),
    call_outcome      = COALESCE(EXCLUDED.call_outcome, sales_recordings.call_outcome),
    notes             = COALESCE(EXCLUDED.notes, sales_recordings.notes),
    external_metadata = sales_recordings.external_metadata || EXCLUDED.external_metadata,
    updated_at        = NOW()
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 4) FIX VIEW: old join on date alone -> cartesian rows on any
--    shared date. Now requires prospect linkage as the original
--    comment promised.
-- ============================================================

CREATE OR REPLACE VIEW v_meetings_with_recordings AS
SELECT
  mn.id AS meeting_id,
  mn.topic,
  mn.meeting_date,
  mn.project,
  mn.summary AS meeting_summary,
  sr.id AS recording_id,
  sr.prospect_name,
  sr.call_outcome,
  sr.audio_file_path
FROM meeting_notes mn
LEFT JOIN sales_recordings sr
  ON sr.call_date = mn.meeting_date
 AND (mn.topic ILIKE '%' || sr.prospect_name || '%'
   OR coalesce(mn.notes,'')   ILIKE '%' || sr.prospect_name || '%'
   OR coalesce(mn.summary,'') ILIKE '%' || sr.prospect_name || '%');

-- ============================================================
-- 5) SEMANTIC SEARCH RPCs (cosine; similarity = 1 - distance)
-- ============================================================

CREATE OR REPLACE FUNCTION search_meetings_semantic(
  query_embedding vector(768),
  match_count INTEGER DEFAULT 10
) RETURNS TABLE (
  id UUID, topic TEXT, meeting_date DATE, project TEXT,
  summary TEXT, notes TEXT, similarity FLOAT
) AS $$
  SELECT mn.id, mn.topic, mn.meeting_date, mn.project,
         mn.summary, mn.notes,
         1 - (mn.embedding <=> query_embedding) AS similarity
  FROM meeting_notes mn
  WHERE mn.embedding IS NOT NULL
  ORDER BY mn.embedding <=> query_embedding
  LIMIT match_count;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION search_sales_semantic(
  query_embedding vector(768),
  match_count INTEGER DEFAULT 10
) RETURNS TABLE (
  id UUID, prospect_name TEXT, call_date DATE, call_outcome TEXT,
  notes TEXT, transcript_path TEXT, similarity FLOAT
) AS $$
  SELECT sr.id, sr.prospect_name, sr.call_date, sr.call_outcome,
         sr.notes, sr.transcript_path,
         1 - (sr.embedding <=> query_embedding) AS similarity
  FROM sales_recordings sr
  WHERE sr.embedding IS NOT NULL
  ORDER BY sr.embedding <=> query_embedding
  LIMIT match_count;
$$ LANGUAGE sql STABLE;

COMMIT;
