|---
name: vision-analysis
description: |-
  Analyze images and extract text using vision tools — Ollama moondream
  with JIT keep_alive lifecycle for VRAM efficiency.
  DO NOT use for: OCR-only tasks (use tesseract), large batch image processing.
category: content
domain: image-processing
intent:
  - image-analysis
  - ocr
  - screenshot-reading
  - vision-llm
exclusions:
  - ocr-only
  - batch-processing
  - video-analysis
requires:
  - ollama
  - moondream
  - vision_analyze
phase: operations
compatible_with: []
conflicts_with: []
handoff_to: []
scope: local-only
data_access:
  mcp_servers: []
  secrets: []
  trust_level: standard
governed_by: []
version: 1.0.0
compatibility:
  min_runtime: hermes-1.0
deprecated: false
deprecation_notes: ""
examples:
  - "Extract text from a screenshot of an invoice"
  - "Describe the contents of a UI mockup image"
  - "Analyze a flowchart screenshot for decision points"
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

### 2. `browser_vision(url, full_page_mode?)`
Use the Hermes browser toolset for screenshots. Use for:
- Rendering a web page and capturing what's actually displayed
- Verifying visual layout or UI states
- Capturing JavaScript-rendered content

**Parameters:**
- `url` — page URL to screenshot
- `full_page_mode` — optional; captures the full scrollable page

## Procedure

1. **Identify what's needed** — text extraction vs visual description vs full page capture
2. **Choose the tool** — `vision__describe_image` for image URL analysis, `browser_vision` for page screenshots
3. **Run the analysis** — use the chosen tool with appropriate parameters
4. **Handle results** — if the result is a description, return it to the user. If text extraction, verify critical data
5. **Memory ingestion (optional)** — if the image contains important business info, use `cognee__memorize` to store extracted knowledge
6. **Error recovery** — if vision tool fails, check if Ollama is running, if the model is pulled, or fall back to text-based alternatives

## Ollama JIT Lifecycle

The vision MCP (`vision_mcp.py`) manages the Ollama model lifecycle:
- On first request: `ollama run moondream` loads the model (~1.7GB VRAM)
- Default `keep_alive: "5m"` — stays loaded 5 minutes after last use, then evicts
- For immediate eviction: the MCP runs `ollama list` and checks residency
- This prevents permanent VRAM occupancy for a model only used occasionally

## Limitations
- ~1.7GB VRAM during use
- Not suitable for batch processing
- Works best with clear, well-lit images
- Text extraction is good but not OCR-perfect — verify critical data
- Local image paths (file://) not supported — must be URLs
