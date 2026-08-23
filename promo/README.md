# The promo films

Five films, one rule, five renderers:

| Film | Renderer | Artefacts |
|---|---|---|
| runtime, 76 s | `render_promo.py` | `artifacts/` |
| navigation, 94 s | `render_nav_promo.py` | `artifacts/nav/` |
| platforms & flight, 85 s | `render_flight_promo.py` | `artifacts/flight/` |
| autonomy, 95 s | `render_stack_promo.py` | `artifacts/stack/` |
| one mission, 106 s | `render_mission_promo.py` | `artifacts/mission/` |

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
other direction too: the runtime film shows ten deadline misses out of 24 000
ticks, and the autonomy film gives a whole scene to the one variant of eight
that tumbled. Both say so on screen rather than cropping to the good part.

The mission film is the strictest case of all, because its claim is that a
prediction made BEFORE the mission flew matched what happened when it did. So
its capture script runs in the order the film shows -- v1 composed and flown,
scored; two edits; v2 scored against V1'S evidence while still unflown; only
then v2 flown -- and nothing is back-filled.

It also gives a whole scene to the stage that does not work. The four-waypoint
survey does not fly closed-loop: the magnetometer's innovation gate cascades,
nothing else observes yaw, and the sortie diverges by hundreds of metres. The
film shows every attempt and names the defect rather than quietly flying a
shorter mission and calling it the same thing.

The autonomy film is the next strictest, because most of what it shows is
arithmetic rather than a trajectory. Its capture script re-runs the statechart
demo, regenerates the mission corpus, re-flies the estimator closed-loop check
and re-sweeps the forge, so every figure on screen is one an artefact file
contains — including the chart, which is displayed verbatim from the file the
engine loads.

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
| `artifacts/flight/*.json` | `capture_flight_artifacts.sh` — real closed-loop runs |
| `artifacts/flight/platforms/*.yaml` | the shipped catalogue, copied verbatim |

Re-run those, drop the output in, re-render. If a number in the film ever
disagrees with what the stack currently does, the artefact is stale — fix the
artefact, never the renderer.

## The platforms & flight film

```sh
./promo/capture_flight_artifacts.sh          # fly all three, plus Gazebo
python3 promo/render_flight_promo.py \
    --artifacts promo/artifacts/flight \
    --out       /tmp/hiko-flight.mp4 \
    --poster    /tmp/hiko-flight-poster.jpg
```

Every ground track in it is the vehicle's actual position over time and every
figure quoted is a metric the flight check computed. The capture script exists
so the film is never re-rendered against numbers somebody typed — it is
re-rendered against the output of a run anyone can repeat.

Published to the site as `landing/media/hiko-flight.mp4`.
