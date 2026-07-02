# Typography — Cinematic HTML Presentation

Reference material for type systems, font stacks, and spacing. Load when creating a new presentation or adjusting headline/body typography.

---

## System Font Stacks

Use built-in system fonts only unless the user explicitly requests external fonts.

| Role | Stack |
|---|---|
| Main UI / display | `ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` |
| Code | `ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace` |
| Italic accent | `Georgia, "Times New Roman", serif` |

---

## Headline Style

- Heavy sans-serif
- Large editorial scale
- Responsive `clamp()` sizing
- Tight but readable tracking
- Italic serif accent words used sparingly

---

## Spacing Guardrails

- Avoid overly tight negative letter spacing
- Large heavy sans-serif headlines should use `letter-spacing` between `-0.055em` and `-0.025em`
- Do not use extremely tight tracking like `-0.075em` unless visually verified
- Add slight `word-spacing` for large headlines when needed
- Check letter spacing on: hero titles, section headers, card titles, framework labels, close slides
- Small uppercase labels may use wide tracking, but body text, metadata, and framework labels must remain easy to scan
- Serif italic accents should be looser than the sans headline, around `-0.018em` to `-0.010em`

---

## Recommended Baselines

```css
h1 {
  letter-spacing: -.048em;
  word-spacing: .045em;
  line-height: .90;
}

h2 {
  letter-spacing: -.041em;
  word-spacing: .025em;
  line-height: 1;
}

h3 {
  letter-spacing: -.034em;
  word-spacing: .018em;
  line-height: 1.02;
}

.serif {
  letter-spacing: -.014em;
}
```
