# Design System — Cinematic HTML Presentation

Reference material for theming and visual direction. Load when creating a new presentation or restyling an existing one.

---

## Semantic Token Names

Use these variable names regardless of which preset is chosen:

```css
:root {
  --bg;           /* page background */
  --bg2;          /* secondary background, sections */
  --panel;        /* glass panel fill */
  --panel2;       /* elevated panel fill */
  --text;         /* primary text */
  --muted;        /* secondary text */
  --faint;        /* tertiary / placeholder text */
  --accent-1;     /* primary accent — buttons, highlights, active states */
  --accent-2;     /* secondary accent — hover, supporting highlights */
  --accent-3;     /* tertiary accent — tags, metadata, rails */
  --accent-4;     /* quaternary accent — diagrams, success states */
  --accent-5;     /* quinary accent — warnings, callouts */
  --accent-6;     /* senary accent — links, info states */
  --accent-7;     /* error / alert states */
  --paper;        /* parchment/warm diagram card background */
  --paper2;       /* parchment border/shadow */
  --ink;          /* parchment text */
  --line;         /* subtle divider / border */
  --glow;         /* box-shadow glow using accent-1 */
  --shadow;       /* card drop shadow */
  --scene-w;      /* max content width */
  --radius;       /* default border radius */
}
```

---

## Preset Palettes

Pick the preset that best fits the topic and audience, or provide a custom one.

### Preset 1 — Dark Cinematic

High contrast, editorial, premium.

```css
:root {
  --bg: #06070d;
  --bg2: #0b0e18;
  --panel: rgba(18,21,34,.72);
  --panel2: rgba(25,28,44,.84);
  --text: #f4f3f5;
  --muted: #a9abb7;
  --faint: #6f7281;
  --accent-1: #ff8b61;
  --accent-2: #d86f4f;
  --accent-3: #9b86ff;
  --accent-4: #59d99a;
  --accent-5: #e9c75f;
  --accent-6: #7fa7ff;
  --accent-7: #ff695f;
  --paper: #efe1c8;
  --paper2: #dbc39a;
  --ink: #4e3324;
  --line: rgba(255,255,255,.12);
  --glow: 0 0 48px rgba(255,139,97,.28);
  --shadow: 0 34px 110px rgba(0,0,0,.48), inset 0 1px 0 rgba(255,255,255,.06);
  --scene-w: min(1220px, calc(100vw - 7vw));
  --radius: 28px;
}
```

### Preset 2 — Light Editorial

Clean, professional, readable.

```css
:root {
  --bg: #f5f4f1;
  --bg2: #eceae4;
  --panel: rgba(255,255,255,.82);
  --panel2: rgba(255,255,255,.96);
  --text: #1a1a1e;
  --muted: #5a5a68;
  --faint: #9a9aaa;
  --accent-1: #1a6ef5;
  --accent-2: #1454c4;
  --accent-3: #7c3aed;
  --accent-4: #059669;
  --accent-5: #d97706;
  --accent-6: #0891b2;
  --accent-7: #dc2626;
  --paper: #fff9ee;
  --paper2: #e8d9b8;
  --ink: #3d2b12;
  --line: rgba(0,0,0,.10);
  --glow: 0 0 48px rgba(26,110,245,.18);
  --shadow: 0 16px 60px rgba(0,0,0,.12), inset 0 1px 0 rgba(255,255,255,.80);
  --scene-w: min(1220px, calc(100vw - 7vw));
  --radius: 28px;
}
```

### Preset 3 — Night Blue

Focused, technical, deep.

```css
:root {
  --bg: #080c14;
  --bg2: #0d1220;
  --panel: rgba(14,20,40,.76);
  --panel2: rgba(20,28,54,.88);
  --text: #e8eaf4;
  --muted: #8b90b0;
  --faint: #5a5f7a;
  --accent-1: #4f9eff;
  --accent-2: #2c7fe0;
  --accent-3: #a78bfa;
  --accent-4: #34d399;
  --accent-5: #fbbf24;
  --accent-6: #22d3ee;
  --accent-7: #f87171;
  --paper: #eef2ff;
  --paper2: #c7d2fe;
  --ink: #1e1b4b;
  --line: rgba(255,255,255,.10);
  --glow: 0 0 48px rgba(79,158,255,.28);
  --shadow: 0 34px 110px rgba(0,0,0,.56), inset 0 1px 0 rgba(255,255,255,.06);
  --scene-w: min(1220px, calc(100vw - 7vw));
  --radius: 28px;
}
```

---

## Applying a Custom Brand Palette

If the user provides specific brand colors, map them to the semantic tokens:

| Brand color | Maps to |
|---|---|
| Primary brand color | `--accent-1` |
| Primary hover / darker shade | `--accent-2` |
| Secondary brand color | `--accent-3` |
| Success / positive | `--accent-4` |
| Warning / highlight | `--accent-5` |
| Info / link | `--accent-6` |
| Error / alert | `--accent-7` |
| Background | `--bg`, `--bg2` |
| Text | `--text`, `--muted`, `--faint` |
| Glow | Recompute using `--accent-1` at low opacity |

---

## Default Visual Direction

Overall feel:
- High contrast background
- Subtle grain
- Radial lighting
- Ambient glow
- Strong contrast
- Editorial, cinematic, premium
- Website-grade polish, not "slides"

Visual motifs to use frequently:
- Masked vertical glow rail or timeline
- Radial scene lighting
- CSS grain/noise texture
- Glass panels with glowing borders
- Capsule labels like `01 · THE QUESTION`
- Color-coded chips
- Hoverable cards
- Terminal/file-tree panels
- Parchment-style diagram cards
- Identity/spec cards
- Interactive layered framework rows
- Inline SVG arrows, rails, loops, and system maps
- Progress dots or progress line
- Subtle cursor glow or ambient glow only if performance remains good

Never use generic bullet-slide layouts as the main structure. Every section needs a distinct composition.
