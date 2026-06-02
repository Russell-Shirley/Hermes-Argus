# Layout — Cinematic HTML Presentation

Reference material for responsive layout, collision prevention, and the center rail system. Load when building a new presentation or fixing layout/responsive issues.

---

## Collision-Proof Layout Rules

Prevent text collisions in all responsive layouts.

**Use:**
- `minmax(0,1fr)` for flexible grid columns
- `min-width: 0` on grid/flex children that contain text
- `gap` and `column-gap` instead of relying on whitespace
- `flex-wrap: wrap` for chip rows
- `overflow: hidden` and `text-overflow: ellipsis` for secondary metadata when needed
- Mobile breakpoints that stack content instead of squeezing it

**Never let:**
- A primary label overlap a secondary label
- A framework title collide with a right-side descriptor
- A chip overflow its container
- A center rail run through important centered content
- A glow line visually touch or cross a headline or panel

---

## Center Rail Rules

A vertical center rail is part of the default cinematic style, but it must never damage readability. Use one of these strategies:

1. Mask the rail behind important centered content
2. Add a `.rail-break` class to sections that need a rail gap
3. Place content above the rail with `z-index` and add a center background mask
4. Move the rail left on mobile
5. Disable or reduce opacity when the composition is dense

The rail gradient and glow must use the active theme's CSS variables, not hardcoded colors.

### Recommended rail pattern

```css
.rail {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  pointer-events: none;
  background: linear-gradient(180deg,
    transparent 0,
    var(--accent-1) 10%,
    var(--accent-3) 30%,
    var(--accent-4) 50%,
    var(--accent-5) 70%,
    var(--accent-6) 86%,
    transparent 100%);
  box-shadow: var(--glow);
  -webkit-mask-image: linear-gradient(to bottom,
    #000 0, #000 var(--rail-gap-start),
    transparent calc(var(--rail-gap-start) + 1px),
    transparent var(--rail-gap-end),
    #000 calc(var(--rail-gap-end) + 1px),
    #000 100%);
  mask-image: linear-gradient(to bottom,
    #000 0, #000 var(--rail-gap-start),
    transparent calc(var(--rail-gap-start) + 1px),
    transparent var(--rail-gap-end),
    #000 calc(var(--rail-gap-end) + 1px),
    #000 100%);
}
```

JavaScript should update `--rail-gap-start` and `--rail-gap-end` based on the active `.rail-break .scene-inner`.

---

## Responsive Breakpoints

### Desktop

- Cinematic, spacious, large type
- Use the center rail when appropriate
- Keep panels aligned and high impact

### Tablet

- Reduce huge gaps
- Stack fragile framework rows when needed
- Preserve visual hierarchy

### Mobile

- Use `scroll-snap-type: y proximity` instead of `mandatory` if necessary
- Move rail to the left or reduce opacity
- Stack split layouts
- Hide side descriptors in framework rows
- Hide progress dots/controls if they clutter the viewport
- Ensure cards, chips, file trees, and diagrams do not overflow

### Mobile baseline

```css
@media (max-width: 900px) {
  html { scroll-snap-type: y proximity; }
  .scene { place-items: start center; padding: 64px 22px; }
  .scene-inner::before { display: none; }
  .rail { left: 28px; opacity: .38; }
  .split,
  .split.reverse { grid-template-columns: 1fr; }
  .controls,
  .dots { display: none; }
}
```
