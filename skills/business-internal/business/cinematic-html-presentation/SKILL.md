|---
name: cinematic-html-presentation
description: |-
  Create or edit standalone, high-fidelity cinematic HTML presentations
  from research briefs, outlines, video notes, scripts, or rough ideas.
  Use this skill when the user asks for an HTML deck, cinematic
  presentation, interactive editorial document, visual explainer,
  scroll-snap story, or wants an existing HTML presentation improved
  while preserving its visual system.
  DO NOT use for: React/Vue/Svelte development, PowerPoint/Google Slides,
  dashboard UI, PDF generation, or static website builds.
category: business
domain: presentation
intent:
  - html-presentation
  - cinematic-deck
  - visual-explainer
exclusions:
  - react-development
  - powerpoint-slides
  - dashboard-ui
  - pdf-generation
requires: []
phase: stable
compatible_with: []
conflicts_with: []
handoff_to: []
scope: liftable
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
  - "Make me an HTML presentation about AI adoption trends"
  - "Build a cinematic deck for our investor pitch"
  - "Turn this research brief into a visual explainer"
  - "I have a video script, turn it into an HTML presentation"
  - "Create a scroll-snap story about our product launch"
---

# Cinematic HTML Presentation Builder

## Mission

Turn a user's research brief, video outline, notes, script, or rough idea into a standalone, polished HTML presentation that feels like a cinematic editorial website — not a generic slide deck.

The output must feel finished on the first pass: high contrast, strong editorial typography, cinematic pacing, distinct section compositions, purposeful interaction, responsive behavior, and no placeholder feel.

The default deliverable is one complete self-contained HTML file with all HTML, CSS, SVG, and JavaScript in a single document.

---

## References

Before generating, load the reference files from `references/` alongside this skill. Skip files not needed for the current task type.

| Task | Load these references |
|---|---|
| New presentation (from scratch) | All five: `design-system.md`, `typography.md`, `components.md`, `layout.md`, `html-architecture.md` |
| Edit existing HTML presentation | `layout.md`, `components.md` |
| Theme or restyle only | `design-system.md`, `typography.md` |
| Fix interactions or accessibility | `html-architecture.md` |
| Fix responsive / mobile issues | `layout.md` |

---

## Content Extraction Workflow

Before writing HTML, internally extract from the user's input:

1. **Topic** — what is this about
2. **Audience** — who will view this
3. **Goal** — what should the viewer understand or do after
4. **Thesis** — the single core argument or insight
5. **Hook** — the opening that earns attention
6. **Core tension** — what people get wrong, why it matters
7. **Mental model shift** — the reframing
8. **Key claims** — 3-5 supporting arguments
9. **Framework** — the system, model, or architecture being presented
10. **Examples** — concrete evidence or case studies
11. **Action steps** — what the viewer should do next
12. **Visual metaphors** — imagery that reinforces the narrative
13. **Tone** — editorial voice and energy level
14. **Constraints** — length, brand, audience restrictions

If the brief is thin, infer a strong narrative and state assumptions briefly only when helpful.

Ask at most 3 clarifying questions only if essential facts are missing. If the user says proceed, proceed.

For current, technical, legal, medical, financial, or fast-changing topics, use research when available and cite sources compactly in the HTML or a final note. Never invent statistics, quotes, claims, or citations.

---

## Narrative Structure

Turn the brief into a story, not a fact dump. Default deck structure:

1. **Hero / title** — Big title, italic thesis/tagline, short explanation, topic chips
2. **Core tension** — What people get wrong, who it affects, why it matters
3. **The shift** — The core mental model or reframing
4. **System architecture** — Framework, timeline, map, workflow, stack, model, or operating system
5. **Main sections** — 3 to 5 sections, each answering one clear question paired with a designed visual
6. **Interactive framework** — Layers, pillars, loop, map, stack, or operating system (interactive when useful)
7. **Practical playbook** — Steps, checklist, prompts, workflow, implementation cards
8. **Recap / close** — Summarize the system and end with a memorable next action

Keep copy tight. Prefer big visual hierarchy over dense paragraphs. Every section needs a distinct composition — never use generic bullet-slide layouts as the main structure.

---

## Theming Workflow

Before writing the HTML:

1. Ask the user if they have a preferred visual direction or brand palette
2. If yes — map their colors to the semantic tokens defined in `references/design-system.md`
3. If no — use the Default Dark Cinematic preset from `references/design-system.md`

All accent colors, backgrounds, and glow values must be driven by CSS custom properties in `:root`. Never hardcode brand colors in individual rules — always reference a variable so the entire theme is swappable from one place.

---

## Output Contract

Always produce one complete standalone HTML file unless the user explicitly asks for something else.

The file must:
- Run locally in a browser without build tools
- Include `<!doctype html>`, `<html>`, `<head>`, `<style>`, `<body>`, and `<script>`
- Use inline SVG, CSS shapes, gradients, procedural texture, and system fonts
- Avoid external CDNs, remote scripts, external fonts, and remote images unless the user explicitly asks
- Use CSS custom properties in `:root`
- Include semantic sections and readable class names
- Include desktop, tablet, and mobile responsive behavior
- Include `prefers-reduced-motion` support
- Include smooth but restrained interactions
- Include no missing assets, no placeholder blocks, and no broken visual elements

When file creation is available, save the result as a versioned `.html` file and return a link or filename.

When file creation is not available, output the full HTML in one code block and tell the user to save it as `index.html` or a descriptive filename.

---

## Quality Bar

The first version must look finished. Before delivery, verify:

- [ ] Clear narrative arc — not a fact dump
- [ ] Distinct section compositions — no repeated layouts
- [ ] Topic-specific visuals — not generic clip art
- [ ] Meaningful interactions — hover states, keyboard nav, progress
- [ ] Offline runnable — no external dependencies
- [ ] No broken or missing assets
- [ ] No placeholder content
- [ ] No generic bullet-slide layouts
- [ ] No decorative rail crossing key content
- [ ] Desktop responsive
- [ ] Tablet responsive
- [ ] Mobile responsive
- [ ] Motion is smooth and optional (reduced motion works)
- [ ] Self-contained file — all CSS and JS inline
- [ ] No headline, card title, framework label, chip, or metadata feels glued together
- [ ] No framework row, card row, or label/sublabel pair overlaps
- [ ] Source section is compact and designed when sources are used
- [ ] All colors reference CSS custom properties — no hardcoded brand values

---

## Editing Existing HTML

When editing an existing HTML presentation:

1. Modify the existing HTML — do not rebuild from scratch unless the user asks
2. Preserve the visual system (theme tokens, component styles)
3. Preserve working interactions
4. Fix bugs directly
5. Return a versioned output file
6. Do not replace the design with a generic template
7. Keep the cinematic quality bar
8. Check for regressions after editing

Common fixes:
- Loosen overly tight headline letter spacing
- Add word spacing to large headlines
- Prevent framework label/sublabel overlap
- Add `minmax(0,1fr)` and `min-width:0`
- Stack crowded layout regions at tablet/mobile widths
- Mask center rails behind key content
- Increase gap between cards or labels
- Fix tooltip positioning
- Fix progress count
- Fix reduced motion mode
- Fix mobile overflow

---

## Delivery Format

When delivering a new HTML presentation:

1. Provide the downloadable HTML link when available
2. Mention the filename
3. Briefly list built-in controls: Arrow / Space / PageDown advance, ArrowUp / PageUp go back, F fullscreen, M reduced motion, U hide UI
4. Ask for specific iteration requests around content, fidelity, motion, layout, or branding

Be decisive, editorial, and practical. Do not over-explain process. Do not call the design a wireframe, draft, or skeleton. The output should feel like a finished cinematic artifact.
