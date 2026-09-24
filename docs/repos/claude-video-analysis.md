# claude-video / `/watch` — Repo Analysis

**Repo:** [bradautomates/claude-video](https://github.com/bradautomates/claude-video)
**Stars:** 9,400 | **Forks:** 1,013 | **License:** MIT
**Language:** Python (112KB) + Shell (6KB)
**Created:** 2026-04-24 | **Last Push:** 2026-07-01

---

## What It Is

A **slash-command skill** (`/watch`) that gives any AI coding agent (Claude Code, Codex, Cursor, Copilot, Gemini CLI, +50 more via [Agent Skills](https://agentskills.io)) the ability to **watch a video** — download, extract scene-aware frames, grab captions or transcribe via Whisper, and hand everything to the agent as images + timestamped transcript.

Blew up fast: 7.2k → 9.4k stars in ~2 weeks.

---

## Architecture

### Single self-contained skill: `skills/watch/`

```
skills/watch/
├── SKILL.md              # Skill contract — the agent reads this when /watch fires
├── .skillignore
└── scripts/
    ├── watch.py          # Entry point: orchestrates download → frames → transcript
    ├── download.py       # yt-dlp wrapper (anything yt-dlp supports: YT, Loom, TikTok, X, etc.)
    ├── frames.py         # ffmpeg frame extraction with auto-fps + dedup
    ├── transcribe.py     # Caption-first, Whisper fallback
    ├── whisper.py        # Groq whisper-large-v3 (preferred) or OpenAI whisper-1
    ├── setup.py          # Preflight/installer (auto-installs brew deps on macOS)
    └── config.py         # Shared config
```

### Plugin manifests for every host:
- `.claude-plugin/plugin.json` + `marketplace.json`
- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `AGENTS.md` → `@CLAUDE.md` generic entry point
- `hooks/` — Claude Code SessionStart hook

### Installation surface

| Surface | Install |
|---------|---------|
| **Claude Code** | `/plugin marketplace add bradautomates/claude-video` then `/plugin install watch@claude-video` |
| **Codex, Cursor, Copilot, Gemini CLI, +50** | `npx skills add bradautomates/claude-video -g` |
| **claude.ai (web)** | Download `watch.skill` from releases → Settings → Skills → `+` |

---

## How It Works

1. **User pastes URL + question.** Anything yt-dlp supports (YouTube, Loom, TikTok, X, Instagram) or local path (`.mp4`, `.mov`, `.mkv`, `.webm`).

2. **yt-dlp checks captions first.** At `transcript` detail level, captioned URLs return without downloading video. Otherwise downloads only what's needed.

3. **ffmpeg extracts frames.** Frame modes:
   - `transcript` — no frames, transcript only (skips download when captions exist)
   - `efficient` — keyframe pass only (cap 50, ~0.5s extraction)
   - `balanced` — scene-change detection (cap 100, ~21s extraction for 49min video)
   - `token-burner` — scene-aware, uncapped

4. **Frame dedup** runs by default: scales each frame to 16×16 grayscale, computes mean absolute difference against last kept frame. Threshold 2.0/255. Drops near-duplicates (held slides, static shots) before billing.

5. **Transcript** from native captions first (free), Whisper fallback (Groq preferred, OpenAI alt).

6. **Agent reads frames + transcript** and answers grounded in what's actually on screen.

---

## Key Technical Details

### Frame budget (auto-capped to prevent token blowout)

| Duration | Default Budget |
|----------|---------------|
| ≤30s | ~30 frames (dense) |
| 30s–1min | ~40 frames |
| 1–3min | ~60 frames |
| 3–10min | ~80 frames |
| >10min | 100 frames capped |

Focused mode (`--start`/`--end`) gets denser budgets up to 2fps within window.

### Cost profile for 49min video

| Mode | Frames | Extract Time | Est. Image Tokens |
|------|--------|-------------|-------------------|
| `transcript` | 0 | ~4.5s | 0 (~26.6k text) |
| `efficient` | 50 | ~0.5s | ~9.8k |
| `balanced` | 100 | ~20.9s | ~19.7k |
| `token-burner` | 116 | ~21.0s | ~22.8k |

### Dependencies
- `yt-dlp` — video/audio download
- `ffmpeg` — frame extraction
- Whisper API (Groq or OpenAI) — only needed when video has no native captions
- Pure stdlib Python — no pip image libraries for dedup

---

## Why It Matters to Us

1. **Directly relevant** — we run Hermes Agent which supports skills. We could install this skill to give our own agents video-watching ability.

2. **Well-designed architecture** — self-contained skill folder, host-agnostic path resolution, no harness-specific env vars. Good pattern reference for our own skill authoring.

3. **Frame dedup approach** — pure stdlib Python via 16×16 grayscale + mean absolute diff. Simple, effective, zero dependencies.

4. **Dual-mode transcription** — captions first (free), Whisper fallback. Same pattern we use in our MeetingRecord pipeline.

5. **Explosive growth** — 9.4k stars in ~2 months. The agent-skills CLI ecosystem is real and growing.

---

## Potential Issues / Limitations

- **Windows support** is second-class — `python3` vs `python`, `brew` doesn't exist, manual `winget`/`pip` instructions only
- **Whisper API dependency** for caption-less videos — not truly local (though `--no-whisper` + frames-only is an option)
- **No Hermes Agent native plugin** — would need to be adapted from the Claude Code plugin format to Hermes' skill system
- **Single threaded** — frame extraction doesn't parallelize across clips
- **57 open issues** at time of analysis — mostly feature requests and edge cases

---

## Verdict

**High-quality, practical, well-architected project.** The `/watch` skill is the kind of capability gap plug that makes agent skills compelling. The architecture is clean — self-contained folder, no harness lock-in, thoughtful token budgeting. Worth installing in our Hermes stack for video analysis tasks, and worth studying as a pattern for our own skill development.
