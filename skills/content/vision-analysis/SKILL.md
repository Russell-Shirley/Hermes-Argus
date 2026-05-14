---
name: vision-analysis
description: "Analyze images and extract text using vision tools. Covers vision__describe_image (Ollama/moondream, local), browser_vision, and when to use which. Includes keep_alive lifecycle tradeoffs, error recovery, and memory ingestion patterns."
category: content
---

# Vision Analysis Skill

## When to Use
- User sends an image or screenshot to Argus via Slack and wants it analyzed
- You need to extract text from a screenshot, diagram, or photo
- A page renders oddly and you need visual confirmation (use `browser_vision`)
- User asks about something in an image file they've shared

## Available Tools

### 1. `vision__describe_image(url, prompt?)`
Fetch an image from a URL and describe it using local Ollama moondream. Use for:
- Screenshots, diagrams, photos, documents sent via Slack
- Text extraction from images (signs, whiteboards, slides, UI screenshots)
- Ingesting image content into Cognee memory

**Parameters:**
- `url` — direct image URL (Slack CDN URLs work)
- `prompt` — optional; defaults to a thorough description prompt

**Image path handling:**
- Slack attachment URLs — pass directly; Hermes provides these in the message context
- HTTPS URLs — work directly
- Local paths on this machine — not supported; only URLs

**Typical invocation pattern when a user sends an image:**
```
1. Call vision__describe_image(url=<slack attachment url>)
2. Call cognee__memorize(text="Image from <date>: " + description)
3. Add 🧠 reaction (brain) after Cognee write confirms
4. Reply with a brief summary of what was found
```

### 2. `browser_vision(question, annotate)`
Take a screenshot of the current browser page and analyze it. Use for:
- Visual verification of rendered pages
- CAPTCHAs and visual challenges
- Complex layouts the text snapshot doesn't capture
- QA checks before reporting results
- When `annotate=true`, overlays numbered labels [N] on interactive elements

**Note:** `browser_vision` uses the host LLM (deepseek-chat), which does NOT support images. This tool fails with a 400 on the current model. Use `vision__describe_image` instead for any image content.

## Error Recovery

### vision__describe_image errors
The tool returns a `[Image could not be described — ...]` string (never raises) so the agent always gets a usable response:

| Returned string | Likely cause | Action |
|---|---|---|
| `HTTP 404` | Bad URL or expired Slack link | Tell user the link expired |
| `vision model unavailable` | Ollama not running / moondream not pulled | Check Ollama, run `ollama pull moondream` |
| `empty response` | Model loaded but returned nothing | Retry once; if persistent, report to user |

Fallback behavior: if vision is unavailable, reply with `[Attachment: <name> — image, could not be described]` and continue — never crash.

### browser_vision / deepseek-chat errors
**Error: "unknown variant `image_url`" (400)**
This is a model capability issue — deepseek-chat does not support images.
- Acknowledge you can't see the image with this model
- Ask the user to paste any relevant text, or use `vision__describe_image` for Slack attachments

## VRAM Lifecycle (`keep_alive`)

Ollama's `keep_alive` controls how long moondream stays in VRAM after a request:

| Value | Behavior |
|-------|----------|
| `"0"` | Evict immediately after the request |
| `"5m"` | Keep warm 5 minutes after last use (default) |
| `"-1"` | Keep loaded indefinitely |

**Default is `"5m"`** — batch screenshots in one session share the warm model, then it self-evicts after 5 idle minutes.

**VRAM contention with Gemma:** if VRAM is tight, Ollama evicts Gemma to load moondream, then reloads Gemma on the next text request (~2 min cold start each way). Options:

| Strategy | Tradeoff |
|----------|----------|
| `VISION_KEEP_ALIVE=0` | Accept per-request cold load, protect Gemma residency |
| `VISION_KEEP_ALIVE=-1` | Pin moondream — only works if VRAM fits both |
| CPU offload (auto) | Ollama automatically layers moondream across GPU/CPU via `num_gpu`. On a 4 GB card, ~20–30 layers land on CPU. No config change needed, but inference is ~3–5× slower. No Gemma eviction. |

**Diagnosing VRAM pressure:** if text responses feel slow after vision use, check if Gemma is reloading by watching `ollama ps` — if moondream appears alone after a chat message, Gemma was evicted and is reloading cold.

## Text Extraction Patterns

**From a Slack screenshot:**
```
vision__describe_image(
    url="https://files.slack.com/files-pri/...",
    prompt="Extract all the text from this image, preserving structure and formatting."
)
```

**From a diagram:**
```
vision__describe_image(
    url="https://...",
    prompt="Describe the structure of this diagram, label all components, and explain the relationships shown."
)
```

**For memory ingestion:**
```
description = vision__describe_image(url=attachment_url)
cognee__memorize(text=f"Screenshot received {date}: {description}")
```

## Pitfalls
- `vision__describe_image` may be slow on first call (~5–15 s) while moondream loads from disk
- HEIC and WebP are not reliably supported — PNG and JPEG are safest
- Very large images may time out — the tool has a 120 s inference timeout
- The tool never raises; it always returns a string, including on errors
- `browser_vision` requires `browser_navigate` to be called first and won't work with deepseek-chat

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `VISION_MODEL` | `moondream` | Ollama model name |
| `VISION_KEEP_ALIVE` | `5m` | VRAM residency after last request |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |

First-time setup: `ollama pull moondream`

Alternative models: `llava` (4.7 GB, solid all-rounder), `minicpm-v` (5.5 GB, stronger at OCR/text-in-image)
