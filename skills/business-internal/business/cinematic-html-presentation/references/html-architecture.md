# HTML Architecture — Cinematic HTML Presentation

Reference material for the default document structure, JavaScript behavior, interactions, and accessibility. Load when building a new presentation or fixing interaction/a11y issues.

---

## Default HTML Structure

Use this structural approach unless the content requires a different layout:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>...</title>
  <style>
    :root {
      /* Swap this block to retheme the entire presentation */
      --bg: ...;
      --bg2: ...;
      --panel: ...;
      --panel2: ...;
      --text: ...;
      --muted: ...;
      --faint: ...;
      --accent-1: ...;
      --accent-2: ...;
      --accent-3: ...;
      --accent-4: ...;
      --accent-5: ...;
      --accent-6: ...;
      --accent-7: ...;
      --paper: ...;
      --paper2: ...;
      --ink: ...;
      --line: ...;
      --glow: ...;
      --shadow: ...;
      --scene-w: min(1220px, calc(100vw - 7vw));
      --radius: 28px;
    }
    /* ... all styles ... */
  </style>
</head>
<body>
  <svg width="0" height="0" aria-hidden="true">
    <!-- inline symbols -->
  </svg>

  <div class="cursor-glow" aria-hidden="true"></div>
  <div class="rail" aria-hidden="true"></div>
  <div class="progress-line" aria-hidden="true"></div>
  <div class="dots" aria-label="Presentation sections"></div>
  <div class="tooltip" id="tooltip"></div>
  <div class="toast" id="toast"></div>

  <main class="deck" id="deck">
    <section class="scene hero center rail-break" data-title="Hook">
      ...
    </section>
    <!-- additional sections -->
  </main>

  <div class="controls" aria-label="Presentation controls">
    ...
  </div>

  <script>
    (() => {
      // ... all JavaScript ...
    })();
  </script>
</body>
</html>
```

---

## Required Interactions

Every presentation should include:

- **Vertical scroll-snap flow**
- **Keyboard navigation:**
  - ArrowDown, Space, PageDown → advance
  - ArrowUp, PageUp → go back
  - F → toggle fullscreen
  - M → toggle reduced motion
  - U → toggle UI chrome
- **Hover states** for cards, chips, buttons, layers, and rows
- **Clickable elements** — framework rows, cards, pills, or layers when useful
- **Tooltips** for chips and interactive objects when useful
- **Live detail panel** for interactive frameworks when useful
- **Progress indicator** — dots, progress line, slide index, or both
- **Smooth but restrained animations** — do not over-animate

---

## Required JavaScript

Implement lightweight vanilla JS only. No external JS libraries.

Required behaviors:
1. `IntersectionObserver` for active scene detection
2. Progress dots creation and active state
3. Scroll navigation function
4. Keyboard event handling
5. Fullscreen toggle
6. Reduced motion toggle
7. UI chrome toggle
8. Tooltip behavior for `[data-tip]`
9. Interactive framework row behavior when present
10. Clickable checklist/playbook behavior when present
11. Rail mask update for `.rail-break` sections when a center rail exists

### JS resilience rules

- Guard against missing optional elements
- Do not throw errors if a component is absent
- Do not assume every section has the same layout

---

## Accessibility and Motion

### Semantic structure

- Use `<main>` and `<section>` elements
- Descriptive `aria-label` for dot navigation and controls
- `aria-hidden="true"` for decorative SVGs
- Focus-visible states for buttons

### Motion rules

- Use fade-up and subtle transforms
- Avoid fast spinning, intense parallax, or excessive cursor effects
- Respect `prefers-reduced-motion`
- Add a manual reduced-motion toggle with M key

### Reduced motion baseline

```css
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
  }
}

body.reduce-motion *,
body.reduce-motion *::before,
body.reduce-motion *::after {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
}
```

---

## Source and Citation Rules

When the topic requires current or factual support:

- Research with reliable sources when available
- Use primary sources for technical subjects
- Add a compact Sources section inside the HTML or a concise final note
- Do not clutter the deck with long citations
- Do not invent citations
- Do not cite claims that are purely the user's opinion or framing

Source cards should look designed, not like default links.
