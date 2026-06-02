# Components — Cinematic HTML Presentation

Reference material for reusable visual components. Load when building a new presentation or editing component-level elements.

---

## Section Composition Patterns

Use a variety of compositions. Do not repeat the same two-column card pattern too often. Each section should have one dominant visual idea.

Good patterns:
- Centered hero with chips
- Split text + terminal panel
- Split text + parchment diagram
- Full-width interactive framework
- Four-card problem grid
- Before/after shift stage
- File-tree architecture panel
- Identity/spec card
- Layered operating system rows with live detail panel
- Parchment loop diagram
- Playbook checklist cards
- Source grid
- System map with inline SVG arrows
- Terminal/code shell
- Horizontal timeline
- Stack of floating cards
- Glass dashboard
- Pinned quote or thesis card

---

## Chips

- Colorful, rounded, hoverable, and optionally tooltip-enabled
- Must support wrapping (`flex-wrap: wrap`)
- Use icons via inline SVG symbols or CSS text glyphs

---

## Glass Panels

- Translucent backgrounds, glowing borders, inset highlights, and blur
- Avoid unreadable transparency

---

## Parchment Cards

- Warm paper gradients, subtle procedural texture, border, inner outline
- Diagram-like SVG or CSS shapes
- Use `--paper`, `--paper2`, and `--ink` tokens for all parchment surfaces

Best for: frameworks, diagrams, maps, loops, hand-drawn explainers, goals.

---

## Terminal / File-Tree Panels

- Monospace, dark shell, top traffic dots, clear folder indentation

Use for: project structures, commands, code snippets, runtime setup, memory/file systems, workflow examples.

---

## Interactive Layered Framework Rows

Must include:
- Fixed number badge
- Main label
- Secondary metadata
- Optional right-side descriptor
- Hover state
- Active state
- Live detail panel or tooltip
- Responsive stacking to avoid overlap

### Collision-safe structure

```css
.layer-row {
  display: grid;
  grid-template-columns: 52px minmax(0,1fr) auto;
  align-items: center;
  column-gap: 22px;
  overflow: hidden;
}

.layer-copy {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0,1fr);
  align-items: baseline;
  column-gap: 12px;
}

.layer-name {
  white-space: nowrap;
}

.layer-sub {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1180px) {
  .layer-copy { display: block; }
  .layer-name,
  .layer-sub { display: block; }
  .layer-sub { margin-top: 5px; }
}

@media (max-width: 900px) {
  .layer-row {
    grid-template-columns: 52px minmax(0,1fr);
  }
  .layer-side { display: none; }
}
```

---

## Playbook Cards

- Cards should be clickable when useful
- Clicking can toggle a done state and show a small toast
