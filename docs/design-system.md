# SecureReflex AI design system

The frontend copies the visual style (not the brand assets) of the Trigger.dev design system: https://trigger.dev/ and the [Refero breakdown](https://styles.refero.design/style/86541d12-7870-4d51-8c47-0880fdb1ea01). Tokens live in `frontend/tailwind.config.js` and `frontend/src/app/globals.css`.

## Mood
"Charging terminal on slate": a matte charcoal canvas, quiet monospaced text, one electric lime accent, and a faint violet/pink syntax glow. Surfaces are flat. Depth comes from surface contrast and 1px hairlines, never drop shadows.

## Colours
| Role | Hex | Use |
|---|---|---|
| Slate Canvas | #1c1e21 | page background, card base |
| Ink Well | #121317 | recessed panes: editor, diff, terminal |
| Graphite Hairline | #3b3e45 | borders, dividers |
| Steel Border | #272a2e | nested/secondary borders |
| Bone / Cloud / Ash / Fog text | #e5e7eb / #d7d9dd / #b5b8c0 / #878c99 | primary → muted text |
| Signal Lime | #a8ff53 | the only filled accent: primary buttons, active nav, LEDs, secure state |
| Syntax palette | violet #9c9af2, event violet #7655fd, pink #fa3abf, greens #afec73 / #d9f07c, magenta #e888f8 | code and icons only |
| Aqua | #479dec | links/info |

Charcoal scale: 100 #e8e9ec · 200 #d7d9dd · 300 #b5b8c0 · 400 #878c99 · 500 #5f6570 · 600 #3b3e45 · 700 #272a2e · 750 #212327 · 800 #1a1b1f · 850 #15171a · 900 #121317 · 950 #0d0e12 · 1000 #0b0c0f.

Severity (always icon + text): CRITICAL #f43f5e, HIGH #fb923c, MEDIUM #fbbf24, LOW #479dec. Secure = lime, insecure = red, pending = pulsing fog ring, skipped = charcoal-500.

## Effects
- Blueprint grid background (1px #15171a lines, radial fade mask)
- Soft glow orbs: `radial-gradient(#566cff26, transparent 70%)`
- Gradient headline text: `#155dfc → #515bfe → #7557ff → #aa4eff`
- Green edge glow on featured cards: `#47ce90`

## Typography
- Headings: Satoshi 500 (600 hero), tracking 0.025em at 20–30px and 0.05em at 36px+
- Body/UI: Geist 400 (500 for buttons and active nav)
- Code: Geist Mono, 14px
- Fonts are self-hosted in `frontend/public/fonts` (licences in `LICENSES.txt`)

## Shape
4px radius for rectangles, fully rounded only for pills and status dots. Buttons: primary = lime fill with dark text; secondary = 1px graphite border; ghost = text only. Hover states use charcoal-750.

## Motion (CSS keyframes, no animation library)
- Easing: ease-out `cubic-bezier(0,0,.2,1)`. UI transitions take 150–300ms, reveals 600–1200ms.
- Keyframes:
  - `enter` / `exit`: fade, slide and scale for panels and dialogs
  - scroll reveal with a stagger
  - `marquee`: scrolling strip of languages, CWEs and providers
  - `moving-lines`: light beams travelling along the timeline connectors
  - `rotation`: rotating glow border while a run is in progress
  - `opacityBlink`: terminal cursor
  - `pulse`: LED dots
  - `accordion-down` / `accordion-up`: expanding finding cards
  - copy → check micro-interaction on code blocks
- Signature effects:
  - a hero code pane that types a vulnerable snippet and then repairs it
  - a streaming run-log terminal on the workbench
  - count-up numbers on the dashboard KPIs
  - line-draw animation on charts
- `prefers-reduced-motion` turns all motion off and shows the final states instead.

## Accessibility
- Every input has a label.
- Status changes are announced with `aria-live`.
- Everything works by keyboard, with a lime focus ring at a 2px offset.
- Text contrast is at least 4.5:1.
