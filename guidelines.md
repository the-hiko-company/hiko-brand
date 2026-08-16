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

## Approved promo imagery

The demo media set (August 2026) is approved promotional imagery. It is hosted
in `the-hiko-company.github.io/landing/media/` and served from
`https://the-hiko-company.github.io/media/` — reference it from there rather
than duplicating the files into other repos.

| File | Frame |
|---|---|
| `01-title.png` | Title card (brand design) |
| `02-conductor-dag.png` | Conductor DAG bring-up, waves + lifecycle states |
| `03-hover-telemetry.png` | Closed-loop hover + step setpoints, telemetry panels |
| `04-square-hero.png` | Autonomous waypoint square — the hero frame |
| `05-gnss-denied.png` | 30 s GNSS blackout, ESKF dead reckoning + recovery |
| `06-mujoco-split.png` | Same mission on hikosim vs MuJoCo (HSB bridge) |
| `07-matrix-outro.png` | Simulator × autopilot matrix + outro |
| `hiko-stack-demo.mp4` | Full 95 s demo (1080p, silent) |
| `hiko-stack-teaser.mp4` | 15 s highlight cut |

**Provenance — and the claim we make with them.** Every trajectory, telemetry
trace, estimator flag, and lifecycle transition in these frames comes from four
real closed-loop flights recorded end-to-end by the stack's own pipeline
(`hiko_recorder` → MCAP → Parquet) — hikosim and MuJoCo plants, Conductor
bring-up, an injected 30 s GNSS blackout, missions run to COMPLETED verdicts.
Nothing was synthesized at render time. Only the title/outro cards are pure
brand design, and playback is time-compressed with the real flight clock shown
on frame.

Usage rules:

- Market them as **real recorded flights in simulation** — never imply hardware
  flights, and never trim away the on-frame honesty labels ("time-dilated",
  "session ...", the FLOWN/ready/roadmap distinction on the matrix card).
- These are the only approved captures of this demo; don't recolor, re-plot, or
  re-render variants. New captures come from re-running the pipeline.
- The full "what you are watching / reproduce it" breakdown lives at
  [the-hiko-company.github.io/docs/demo](https://the-hiko-company.github.io/docs/demo/).

## Naming

- Org in prose: "The Hiko Company". Product: "the Hiko Stack".
- Repos: `hiko-*` kebab-case. Packages: `hiko_*` snake_case.
- "Hiko" is a Māori word for lightning/electricity — when introducing the brand,
  credit the meaning respectfully; don't use other Māori terms decoratively.
