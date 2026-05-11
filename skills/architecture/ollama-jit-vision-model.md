---
name: ollama-jit-vision-model
description: Pattern for JIT (just-in-time) loading of Ollama vision models on demand — load when image arrives, evict from VRAM immediately after, avoiding permanent VRAM residency.
trigger: When designing image/screenshot ingestion, vision LLM integration, or any feature that needs a model loaded only occasionally.
category: architecture
metadata:
  hermes:
    tags: [ollama, vision, moondream, vram, jit, images, screenshots, memory]
    related_skills: [autonomous-memory-stack]
---

# Ollama JIT Vision Model Pattern

## The Problem

Loading a vision model permanently wastes VRAM. Argus already has a 9.6GB Gemma model. Adding moondream (1.7GB) as a permanent resident means both compete for VRAM — one evicts the other on every request, causing repeated 2-minute cold starts.

## The Solution: `keep_alive`

Every Ollama API request accepts a `keep_alive` field controlling how long the model stays in VRAM after the request completes.

| Value | Behavior |
|---|---|
| `"0"` | Evict from VRAM immediately after this request |
| `"5m"` | Stay warm for 5 minutes after last use (Ollama default) |
| `"-1"` | Stay loaded indefinitely |

Setting `keep_alive: "0"` makes Ollama load the model, run inference, return the result, and evict — all in one call. No manual unload step.

## Implementation

```typescript
// src/vision.ts
export async function describeImage(base64: string): Promise<string> {
  const res = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: process.env.VISION_MODEL ?? 'moondream',
      prompt: 'Describe this screenshot in detail, including any text, UI elements, data, or key information visible.',
      images: [base64],
      keep_alive: '0',   // JIT evict — do not hold VRAM between images
      stream: false,
    }),
  });
  const json = await res.json() as { response: string };
  return json.response;
}
```

## VRAM Tradeoff Table

| keep_alive | VRAM cost | Latency |
|---|---|---|
| `"0"` | Zero between images | Cold load per image (~5–15s for moondream) |
| `"5m"` | ~1.7GB for up to 5 min idle | Warm for burst sessions, auto-evicts |
| `"-1"` | ~1.7GB always | Zero latency, but evicts Gemma permanently |

**Recommendation:** `"5m"` for interactive use (batch of screenshots in one session share the warm model), `"0"` for overnight/background tasks where latency doesn't matter.

## Recommended Model: moondream

- Size: ~1.7GB
- Pull: `ollama pull moondream`
- Strengths: fast, UI/screenshot description, text-in-image reading
- Endpoint: `http://localhost:11434` (same as existing embedding calls)
- Privacy: fully local, no image data leaves the machine

## Fallback Options (no Ollama pull required)

- **OpenRouter free tier:** `meta-llama/llama-3.2-11b-vision-instruct:free` or `qwen/qwen-2.5-vl-7b-instruct:free` — rate-limited but zero setup
- **Gemini 2.0 Flash:** free tier (1,500 req/day), requires `GEMINI_API_KEY`

## Fits the Argus JIT Philosophy

This mirrors the existing JIT skill-loading pattern (`core__read_skill` loads markdown on demand). The agent loads capabilities only when needed — skills from disk, vision model into VRAM — and releases them when done. Neither pattern holds resources between uses.

## GitHub Issue

Implementation tracked at: https://github.com/Russell-Shirley/Hermes-Argus/issues/5
