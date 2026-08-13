# hiko-brand

```
  ╦ ╦ ╦ ╦╔═ ╔═╗
  ╠═╣ ║ ╠╩╗ ║ ║   THE HIKO COMPANY
  ╩ ╩ ╩ ╩ ╩ ╚═╝   aerial autonomy, electrified
```

Brand assets for The Hiko Company: the logo suite, the palette, the landing page,
and the rules for using them. If it carries the Hiko name, it starts here.

## Contents

| Path | What's inside |
|---|---|
| `logo/` | Hand-authored SVG suite: mark (bolt-through-delta-wing), horizontal lockups, mono/white/dark variants, favicon |
| `palette/` | `colors.md` (roles + contrast rules), `tokens.css` (CSS custom properties), `tokens.yaml` (for tooling) |
| `landing/` | Self-contained static landing page: `index.html` + `style.css` + `app.js` — no frameworks, no CDNs |
| `guidelines.md` | Voice, spacing, do/don't — read before using any asset |

## Quick use

Embed the mark (dark surface):

```html
<img src="logo/mark.svg" alt="The Hiko Company" width="48">
```

Dark/light-aware lockup in a GitHub README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".../hiko-brand/main/logo/lockup-horizontal-white.svg">
  <img alt="The Hiko Company" src=".../hiko-brand/main/logo/lockup-horizontal-dark.svg">
</picture>
```

Pull the palette into a stylesheet:

```css
@import url("palette/tokens.css");
h1 { color: var(--hiko-lightning); background: var(--hiko-night); }
```

## Landing page

`landing/` deploys as-is to any static host — copy the three files and done:

```sh
python3 -m http.server -d landing 8080   # preview at http://localhost:8080
```

Dark-native, fully responsive, honors `prefers-reduced-motion` (the hero canvas
falls back to a static field). No external requests of any kind.

## CI

`.github/workflows/ci.yml` validates that every SVG parses (`xmllint`) and lints
the landing page HTML with `tidy` when available (skipped gracefully otherwise).

## License

Proprietary — see [LICENSE](LICENSE). These assets identify The Hiko Company and
may not be used outside org projects.
