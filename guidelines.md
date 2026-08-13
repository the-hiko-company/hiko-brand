# Hiko Brand Guidelines

How The Hiko Company looks and sounds. The assets in this repo are the only
approved versions — never redraw, restyle, or re-color the mark.

## Voice

Bold, engineering-first, slightly electric.

- **Say what the thing does.** "An ESKF that shrugs off GNSS dropout" beats
  "industry-leading navigation solutions."
- **Precision is the flex.** Numbers, units, frames, and named algorithms are
  on-brand; superlatives are not.
- **Electric, not shouty.** One spark per paragraph — a sharp verb or a lightning
  reference — then back to engineering. Never more than one exclamation mark per
  page, and preferably zero.
- **English everywhere.** Short sentences. Active voice. No lorem ipsum, ever.

Tagline (exact, always this punctuation):
**"The aerial autonomy stack. Any airframe. Any autopilot. Anywhere."**
Sign-off line: *aerial autonomy, electrified* (always lowercase).

## The mark

The mark is a lightning bolt striking through a delta wing: the bolt is Hiko
(lightning), the wing is flight. Files in `logo/`:

| File | Use |
|---|---|
| `mark.svg` | Color mark on dark surfaces (default) |
| `mark-white.svg` | All-white mark on dark/photo surfaces |
| `mark-dark.svg` | All near-black mark on light surfaces |
| `mark-mono.svg` | Single-color contexts; inherits `currentColor` |
| `lockup-horizontal.svg` | Color lockup with wordmark, dark surfaces |
| `lockup-horizontal-white.svg` | All-white lockup, dark surfaces |
| `lockup-horizontal-dark.svg` | Near-black lockup, light surfaces |
| `favicon.svg` | Browser tab / app icon only |

### Spacing & sizing

- **Clear space**: keep a margin of at least the bolt's width (half the mark
  height) on all sides of the mark or lockup. Nothing enters that zone.
- **Minimum sizes**: mark 16 px; horizontal lockup 140 px wide. Below that, use
  the favicon tile.
- The lockup's wordmark is drawn as geometric letter paths (renderer-independent
  — it never depends on installed fonts). Do not retype it in a font; the tagline
  line uses the system mono stack and may reflow slightly, which is fine.

### Do

- Use `mark.svg` on `#0B0E14` or darker imagery.
- Use the dark variants on white/light backgrounds.
- Scale proportionally from the SVG sources.
- Pair the mark with the ASCII wordmark in READMEs and terminals.

### Don't

- Don't rotate, skew, outline, add gradients or drop shadows to the mark
  (the landing hero's glow is a page effect, not part of the asset).
- Don't recolor: yellow bolt + blue wing, or a single approved mono color —
  nothing else.
- Don't place the color mark on mid-gray or busy backgrounds where the wing
  loses contrast.
- Don't set the wordmark in title case ("The Hiko Company" is prose; the
  wordmark is always THE HIKO COMPANY).
- Don't stretch the lockup to fit a container; crop the container instead.

## Color

Core palette (see `palette/colors.md` for the full set and contrast rules):

- Lightning `#F5C518` — the event color: CTAs, accents, the bolt.
- Ion `#3EC5FF` — the system color: links, telemetry, the wing.
- Night `#0B0E14` — the ground. Never pure black.

One accent dominant per composition: yellow leads, blue supports.

## Type

- UI/marketing: system grotesk stack (`--hiko-font-sans` in `palette/tokens.css`).
- Code, telemetry, taglines, experiment codenames: mono stack
  (`--hiko-font-mono`). Codenames are always lowercase mono: `h3x`,
  `vda5050-air`, `gnss-denied`.

## Naming

- Org in prose: "The Hiko Company". Product: "the Hiko Stack".
- Repos: `hiko-*` kebab-case. Packages: `hiko_*` snake_case.
- "Hiko" is a Māori word for lightning/electricity — when introducing the brand,
  credit the meaning respectfully; don't use other Māori terms decoratively.
