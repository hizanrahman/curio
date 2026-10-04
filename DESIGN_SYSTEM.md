# Soft Pop design system

The frontend uses a light-first Soft Pop theme for a friendly, focused study space. Global styles and source tokens live in [`frontend/src/index.css`](./frontend/src/index.css); Tailwind semantic colors and font families map to those CSS variables in [`frontend/tailwind.config.js`](./frontend/tailwind.config.js).

## Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#FFF8EC` | Warm page background |
| `--surface` | `#FFFFFF` | Reading surfaces, inputs, and neutral cards |
| `--ink` | `#17171C` | Body copy, outlines, and hard shadows |
| `--muted` | `#5E5E6B` | Supporting copy |
| `--primary` | `#6C5CE7` | Main actions and focus rings |
| `--primary-ink` | `#FFFFFF` | Text on primary actions |
| `--yellow` | `#FFD84D` | Highlight, attempt, and developing accents |
| `--mint` | `#7ADFB5` | Mastery and positive progress |
| `--coral` | `#FF8A7A` | Needs-practice and error surfaces |
| `--sky` | `#8CC8FF` | Student messages and secondary accents |
| `--lilac` | `#C9B8FF` | Tutor prompts and concept accents |
| `--status-neutral` | `#64646E` | Neutral not-assessed status outline and label |
| `--radius` | `16px` | Cards |
| `--radius-control` | `12px` | Buttons and inputs |
| `--shadow-hard` | `4px 4px 0 var(--ink)` | Card depth |
| `--shadow-hard-hover` | `6px 6px 0 var(--ink)` | Hover lift |
| `--motion-duration` | `180ms` | Micro-interaction duration |
| `--motion-stagger` | `70ms` | Entrance stagger |

Display text uses Bricolage Grotesque; body and controls use Inter; code and numeric values use JetBrains Mono. These fonts are bundled locally through `@fontsource-variable` and use `font-display: swap`. System fallbacks are declared in the CSS variables.

## Theme swapping

To recolor the app, edit the palette and shape variables in the `:root` block in `frontend/src/index.css`. Components and Tailwind utilities consume those semantic variables rather than maintaining per-page color palettes. To change font families, update `--font-display`, `--font-body`, or `--font-mono` in the same block and import the matching `@fontsource` CSS in `frontend/src/main.tsx`. No dark-mode variant is enabled for this light-only theme.

## Shared components

Shared components do not own application or API state (the demo keeps only local presentation state for its animation):

```tsx
<ThemeCard variant="mint">A success or progress panel</ThemeCard>
<ThemeButton variant="secondary">Try again</ThemeButton>
<StatusPill status="developing" />
<IndependenceRing score={72} />
<StatChip label="hints used" value={2} />
<EmptyState title="Your first idea is waiting." description="Bring a question to get started." />
```

- `ThemeCard` supports white, yellow, mint, lilac, sky, and coral surfaces.
- `ThemeButton` provides primary, secondary, and ghost button styles.
- `StatusPill` always pairs a status label with an icon and a distinct color.
- `IndependenceRing` is a presentational percentage ring; callers must provide a measured value or a clearly explained estimate.
- `StatChip` displays a supplied value and optional icon.
- `DemoConversation` is a small, local-only looping example; it makes no API requests and stops cycling when reduced motion is preferred.
- `EmptyState` provides original inline SVG illustrations and optional action content.
- The existing Sonner toaster is mounted globally with the shared surface, ink, outline, and shadow tokens.

Use the CSS component classes `theme-card`, `theme-button`, and `theme-input` to keep outlines, shadows, focus, and interaction treatment consistent. Interactive controls retain visible focus rings; motion is limited to transform/opacity and honors `prefers-reduced-motion`.

## Accessibility and responsive behavior

- Body copy uses the ink/muted tokens on cream or white; pastel panels use dark ink copy.
- Controls are keyboard-operable, have minimum touch-friendly heights, and have explicit accessible names where their icon alone would otherwise be ambiguous.
- Tutor messages are announced through a polite live region.
- The workspace becomes a three-column layout at desktop widths and uses Problem, Tutor, Map, and Progress tabs on small screens.
- The concept map uses the persisted, question-specific Socratic objective, prerequisite concepts, and directed relationships from the session plan; it does not fall back to generic placeholder concepts or invented sequential edges. It keeps a compact text-list view, including icon and status label, for narrow layouts, and offers an accessible full-screen expansion with Escape/backdrop/close-button dismissal.
