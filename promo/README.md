# The runtime promo film

`render_promo.py` renders the 76-second Hiko runtime film — 1824 frames at
24 fps, Pillow for the frames and ffmpeg for the encode. No motion-graphics
toolchain, so it runs anywhere the rest of the stack runs and the film can be
re-rendered from a script diff rather than from someone's laptop.

## The rule this file exists to enforce

**Everything on screen is a real artefact produced by the stack.** The timing
report is a real 20-second run, the learning curve is a real training record,
the memory plan is real `hiko-plan` output. They live in `artifacts/` and the
renderer reads them; there is no path through this script that draws an invented
number.

That is not decoration. A promo built on numbers nobody can reproduce is a promo
that does not survive its first demo, and the honesty is load-bearing in the
other direction too: the run shown has ten deadline misses out of 24 000 ticks,
and the film says so on screen rather than cropping to the good part.

## Reproducing

```sh
python3 promo/render_promo.py \
    --artifacts promo/artifacts \
    --out       /tmp/hiko-platform.mp4 \
    --poster    /tmp/hiko-platform-poster.jpg
```

Needs Pillow, ffmpeg, and DejaVu fonts. The output is published to the site as
`landing/media/hiko-platform.mp4` in `the-hiko-company.github.io`.

## Refreshing the artefacts

| File | Where it comes from |
|---|---|
| `artifacts/timing_real.txt` | `hiko_sdk_quadrotor --real` (hiko-sdk), stdout |
| `artifacts/plan.txt` | `hiko-plan examples/quadrotor.yaml` (hiko-os), stdout |
| `artifacts/rl_run.json` | `python3 -m hiko_rl.playground.train` (hiko-rl), run record |

Re-run those, drop the output in, re-render. If a number in the film ever
disagrees with what the stack currently does, the artefact is stale — fix the
artefact, never the renderer.
