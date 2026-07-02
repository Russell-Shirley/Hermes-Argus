-- ============================================================
-- Open Brain: Meeting Notes & Sales Recordings Schema
-- ============================================================
-- Two structured areas for storing knowledge in OpenBrain
-- Applied via: docker exec argus-openbrain psql -U postgres -d openbrain -f schema/openbrain-meetings.sql
-- ============================================================

-- ============================================================
-- SECTION 1: MEETING NOTES
-- ============================================================

CREATE TABLE IF NOT EXISTS meeting_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  meeting_date DATE NOT NULL,
  participants JSONB DEFAULT '[]'::jsonb,
  duration_minutes INTEGER,
  project TEXT,
  transcript_path TEXT,
  summary TEXT,
  notes TEXT,
  external_metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meeting_notes_date ON meeting_notes(meeting_date DESC);
CREATE INDEX IF NOT EXISTS idx_meeting_notes_project ON meeting_notes(project);
CREATE INDEX IF NOT EXISTS idx_meeting_notes_topic ON meeting_notes USING gin(to_tsvector('english', coalesce(topic, '')));

-- ============================================================
-- SECTION 2: SALES CALL RECORDINGS
-- ============================================================

CREATE TABLE IF NOT EXISTS sales_recordings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prospect_name TEXT NOT NULL,
  call_date DATE NOT NULL,
  rep_name TEXT,
  duration_seconds INTEGER,
  audio_file_path TEXT,
  transcript_path TEXT,
  call_outcome TEXT CHECK (call_outcome IN ('booked', 'follow_up', 'no_interest', 'lost', 'other')),
  notes TEXT,
  external_metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_recordings_date ON sales_recordings(call_date DESC);
CREATE INDEX IF NOT EXISTS idx_sales_recordings_prospect ON sales_recordings(prospect_name);
CREATE INDEX IF NOT EXISTS idx_sales_recordings_outcome ON sales_recordings(call_outcome);

-- ============================================================
-- HELPER: Upsert a meeting note
-- ============================================================
-- Usage: SELECT upsert_meeting_note('topic', '2026-07-02', '["Alice","Bob"]'::jsonb, 30, 'ProjectX');
-- Returns the UUID of the inserted row.

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
  INSERT INTO meeting_notes (topic, meeting_date, participants, duration_minutes, project, transcript_path, summary, notes, external_metadata)
  VALUES (p_topic, p_meeting_date, p_participants, p_duration_minutes, p_project, p_transcript_path, p_summary, p_notes, p_external_metadata)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- HELPER: Upsert a sales recording
-- ============================================================
-- Usage: SELECT upsert_sales_recording('Acme Corp', '2026-07-01', 'Russell', 2400, '/path/to/audio.mp3');
-- Returns the UUID of the inserted row.

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
  INSERT INTO sales_recordings (prospect_name, call_date, rep_name, duration_seconds, audio_file_path, transcript_path, call_outcome, notes, external_metadata)
  VALUES (p_prospect_name, p_call_date, p_rep_name, p_duration_seconds, p_audio_file_path, p_transcript_path, p_call_outcome, p_notes, p_external_metadata)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEW: Recent meetings with sales call linkage
-- ============================================================
-- Joins meetings to related sales calls by fuzzy date and prospect name in notes

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
LEFT JOIN sales_recordings sr ON sr.call_date = mn.meeting_date;

-- ============================================================
-- SHARED TRIGGER FUNCTION: auto-update updated_at
-- ============================================================
-- OB1 convention: one shared function, applied per-table via trigger.
-- Safe to run multiple times (CREATE OR REPLACE).

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS: Auto-update updated_at on row change
-- ============================================================

DROP TRIGGER IF EXISTS update_meeting_notes_updated_at ON meeting_notes;
CREATE TRIGGER update_meeting_notes_updated_at
    BEFORE UPDATE ON meeting_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sales_recordings_updated_at ON sales_recordings;
CREATE TRIGGER update_sales_recordings_updated_at
    BEFORE UPDATE ON sales_recordings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
