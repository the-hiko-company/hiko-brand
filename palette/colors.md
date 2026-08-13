# Hiko Palette

The Hiko palette is built for dark cockpits: near-black ground, lightning-yellow
strike, ion-blue signal. Yellow is the *event* color — it marks action, energy,
emphasis. Blue is the *system* color — links, telemetry, structure. Everything
else stays quiet.

## Core

| Token | Hex | Role |
|---|---|---|
| `hiko-lightning` | `#F5C518` | Primary accent — CTAs, highlights, the bolt |
| `hiko-ion` | `#3EC5FF` | Secondary accent — links, telemetry, the wing |
| `hiko-night` | `#0B0E14` | Ground — primary background |

## Extended (derived)

| Token | Hex | Role |
|---|---|---|
| `hiko-night-raised` | `#121724` | Raised surfaces: cards, panels |
| `hiko-night-line` | `#232B3D` | Hairlines, borders, dividers |
| `hiko-cloud` | `#E8EAF0` | Primary text on dark |
| `hiko-haze` | `#9AA3B5` | Secondary text on dark |
| `hiko-lightning-dim` | `#B8940F` | Yellow for large fills / hover-pressed |
| `hiko-ion-dim` | `#2A8DBD` | Blue for large fills / visited states |
| `hiko-alert` | `#FF5D5D` | Errors, failsafe states only |

## Usage rules

- Yellow on night passes AA for text at any size (contrast ≈ 11:1). Never place
  yellow text on white; use `hiko-night` text instead.
- Ion blue is for interactive and informational elements — never for warnings.
- Backgrounds are `hiko-night` first; `hiko-night-raised` only to lift a surface.
  No pure `#000000`.
- One accent dominant per composition: yellow leads, blue supports. If everything
  glows, nothing strikes.

Tokens are shipped as CSS custom properties (`tokens.css`) and YAML for tooling
(`tokens.yaml`). Those two files are the source of truth; keep this document in
sync with them.
