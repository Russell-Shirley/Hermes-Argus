---
name: vision-analysis
description: |
  Analyze images and extract text using vision tools. Covers Ollama + moondream
  (1.7GB local model) with JIT keep_alive lifecycle for VRAM efficiency.
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

## Architecture
- **Model:** moondream (1.7GB) via Ollama
- **Lifecycle:** JIT keep_alive — loaded on demand, evicted immediately after
- **VRAM impact:** ~1.7GB during analysis, released after

## Usage
Use the `vision_analyze` tool with:
- `image_url`: path to local image or URL
- `question`: what you need extracted

The tool returns both a description and the specific answer.

## JIT Lifecycle Pattern
The Ollama model uses `keep_alive: "5m"` by default. After the analysis completes, the model is evicted from VRAM. This prevents permanent VRAM residency for a model only used occasionally.

## Limitations
- 1.7GB VRAM during use
- Not suitable for batch processing (load/unload overhead per image)
- Works best with clear, well-lit images
- Text extraction is good but not OCR-perfect — verify critical data
