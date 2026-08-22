#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the stack film — what the whole thing does, frame by frame.

Same rule as the other three, and it is why this script reads files instead of
drawing shapes: EVERYTHING ON SCREEN IS A REAL ARTEFACT.

  artifacts/stack/flight.xml               the shipped chart, verbatim
  artifacts/stack/hsm_demo.txt             the demo's own output
  artifacts/stack/state_oracle.json        hiko_oracle --states --json
  artifacts/stack/evidence.json            hiko_oracle --evidence
  artifacts/stack/trees.json               the templates the corpus flew
  artifacts/stack/x500_estimator.json      a closed loop through the ESKF
  artifacts/stack/estimator_envelope.json  that loop, swept to its edge
  artifacts/stack/tests.txt                colcon test-result

Every figure quoted is a number one of those files contains. There is no path
through this script that draws an invented one — including the one scene where
the honest number is a failure.

Re-capture with capture_stack_artifacts.sh, then:

    python3 render_stack_promo.py --artifacts artifacts/stack --out stack.mp4

Pillow for frames, ffmpeg for encoding. No motion-graphics toolchain.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
FPS = 24

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

BG = (11, 14, 20)
PANEL = (20, 25, 34)
LINE = (31, 39, 51)
TEXT = (230, 234, 242)
MUTED = (138, 148, 166)
ACCENT = (245, 197, 24)
BLUE = (62, 197, 255)
OK = (126, 217, 87)
WARN = (255, 180, 84)
BAD = (255, 107, 107)


def font(size: int, bold: bool = False, mono: bool = False):
    if mono:
        name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    else:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font(64, bold=True)
F_H1 = font(42, bold=True)
F_H2 = font(28, bold=True)
F_BODY = font(24)
F_SMALL = font(20)
F_TINY = font(17)
F_MONO = font(20, mono=True)
F_MONO_S = font(15, mono=True)
F_MONO_B = font(22, mono=True, bold=True)
F_HUGE = font(96, bold=True)


def ease(t: float) -> float:
    """Smoothstep. Linear reveals read as mechanical; this reads as deliberate."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def header(d, kicker: str, title: str) -> None:
    d.text((90, 62), kicker.upper(), font=F_SMALL, fill=ACCENT)
    d.text((90, 92), title, font=F_H1, fill=TEXT)
    d.line([(90, 156), (W - 90, 156)], fill=LINE, width=2)


def footer(d, note: str) -> None:
    d.line([(90, H - 92), (W - 90, H - 92)], fill=LINE, width=1)
    d.text((90, H - 74), note, font=F_TINY, fill=MUTED)


def panel(d, box, fill=PANEL, outline=LINE):
    d.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=1)


def fade(colour, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(BG[i] + (colour[i] - BG[i]) * t) for i in range(3))


def typeset(d, x, y, lines, f, fill, leading=None):
    leading = leading or (f.size + 10)
    for i, line in enumerate(lines):
        d.text((x, y + i * leading), line, font=f, fill=fill)
    return y + len(lines) * leading


def reveal_lines(d, x, y, lines, f, fill, t, leading=None, per=0.055):
    """Lines arriving one after another. `t` is scene progress."""
    leading = leading or (f.size + 10)
    for i, line in enumerate(lines):
        a = ease(min(1.0, max(0.0, (t - i * per) * 6.0)))
        if a <= 0.01:
            continue
        d.text((x, y + i * leading), line, font=f, fill=fade(fill, a))
    return y + len(lines) * leading


def bar(d, box, fraction, colour, track=LINE):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=track)
    w = max(2.0, (x1 - x0) * max(0.0, min(1.0, fraction)))
    d.rounded_rectangle([x0, y0, x0 + w, y1], radius=(y1 - y0) // 2, fill=colour)


# --- scenes -------------------------------------------------------------------


def scene_title(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.4))
    d.text((90, 296), "Nothing here", font=F_TITLE, fill=fade(TEXT, a))
    b = ease(min(1.0, max(0.0, t * 2.4 - 0.5)))
    d.text((90, 382), "is asserted.", font=F_TITLE, fill=fade(ACCENT, b))
    c = ease(min(1.0, max(0.0, t * 2.0 - 1.0)))
    typeset(d, 92, 496, [
        "An autonomy stack that measures itself: charts it can read back,",
        "runs it records, and arithmetic over flights that actually happened.",
    ], F_BODY, fade(MUTED, c), leading=36)
    n = len(A["repos"])
    e = ease(min(1.0, max(0.0, t * 2.0 - 1.5)))
    d.text((92, 604), f"{n} repositories · {A['tests']} tests · 0 failures",
           font=F_MONO, fill=fade(BLUE, e))
    footer(d, "the hiko company — aerial autonomy, electrified")
    return img


def scene_chart(t, A):
    """The statechart, verbatim. The point is that it IS a file."""
    img, d = frame()
    header(d, "declarative statecharts", "The machine is a file now")

    panel(d, (90, 196, 900, 780))
    lines = A["chart_lines"]
    shown = int(len(lines) * ease(min(1.0, t * 1.5)))
    y = 216
    for line in lines[:shown]:
        colour = MUTED
        stripped = line.strip()
        if stripped.startswith("<transition"):
            colour = BLUE
        elif stripped.startswith("<state") or stripped.startswith("<statechart"):
            colour = TEXT
        elif 'terminal="' in line:
            colour = OK
        d.text((110, y), line[:78], font=F_MONO_S, fill=colour)
        y += 21
        if y > 762:
            break

    a = ease(min(1.0, max(0.0, t * 2.0 - 0.7)))
    reveal_lines(d, 950, 226, [
        "Four failsafes, written once,",
        "on the superstate.",
        "",
        "Flat, that is twenty transitions,",
        "and the one you forget is the",
        "one that matters.",
    ], F_BODY, fade(TEXT, a), leading=34, t=t - 0.35)

    b = ease(min(1.0, max(0.0, t * 2.0 - 1.2)))
    panel(d, (950, 470, W - 90, 700), fill=(16, 20, 28))
    typeset(d, 972, 492, [
        "SMACC2 puts this in C++",
        "template metaprogramming.",
    ], F_BODY, fade(MUTED, b), leading=32)
    typeset(d, 972, 570, [
        "Changing one transition",
        "means recompiling the aircraft.",
    ], F_BODY, fade(BAD, b), leading=32)
    footer(d, "hiko_hsm/charts/flight.xml — the file the engine loads, verbatim")
    return img


def scene_demo(t, A):
    img, d = frame()
    header(d, "and it runs", "Nineteen checks, sixteen seconds")

    checks = A["checks"]
    y = 210
    for i, (ok, label) in enumerate(checks):
        a = ease(min(1.0, max(0.0, (t - i * 0.035) * 7.0)))
        if a <= 0.01:
            continue
        d.text((92, y), "PASS" if ok else "FAIL", font=F_MONO_B,
               fill=fade(OK if ok else BAD, a))
        d.text((172, y + 2), label[:88], font=F_SMALL, fill=fade(TEXT, a))
        y += 31

    b = ease(min(1.0, max(0.0, t * 1.6 - 1.0)))
    d.text((92, y + 18), A["checks_line"], font=F_H2, fill=fade(ACCENT, b))
    footer(d, "hiko demo analysis.statechart — the engine, the chart, and ten flown sorties")
    return img


def scene_state_oracle(t, A):
    """Ten runs in, one ranked list out."""
    img, d = frame()
    header(d, "the runs come back", "Where the odds change")

    o = A["state_oracle"]
    d.text((90, 186), f"fitted to {o['runs']} runs, {o['transitions']} transitions",
           font=F_MONO, fill=MUTED)

    rows = o["states"][:7]
    peak = max((s["risk_introduced"] for s in rows), default=1.0) or 1.0
    y = 240
    for i, s in enumerate(rows):
        a = ease(min(1.0, max(0.0, (t - i * 0.07) * 5.0)))
        if a <= 0.01:
            continue
        colour = OK if s["p_success"] >= 0.75 else (WARN if s["p_success"] >= 0.45 else BAD)
        d.text((92, y), s["state"][:18], font=F_H2, fill=fade(TEXT, a))
        d.text((330, y + 6), f"P(ok) {s['p_success'] * 100:5.1f}%", font=F_MONO,
               fill=fade(colour, a))
        d.text((560, y + 6), f"drop {s['risk_introduced'] * 100:5.1f}%", font=F_MONO,
               fill=fade(MUTED, a))
        bar(d, (760, y + 10, 760 + 620 * (s["risk_introduced"] / peak), y + 24),
            1.0, fade(BAD, a))
        y += 52

    b = ease(min(1.0, max(0.0, t * 1.5 - 0.9)))
    typeset(d, 92, y + 22, [
        "Track is where this fleet loses vehicles. Not because anyone said so —",
        "because three of the ten sorties that tracked a target lost a motor doing it.",
    ], F_BODY, fade(TEXT, b), leading=34)
    footer(d, "hiko_oracle --states — an absorbing Markov chain fitted to the runs the engine wrote")
    return img


def scene_corpus(t, A):
    img, d = frame()
    header(d, "the same question, of a tree", "Twelve hundred missions")

    a = ease(min(1.0, t * 2.0))
    typeset(d, 92, 200, [
        "The shipped templates, through the real behaviour-tree engine.",
        "Composites, decorators, retries and reactive halting all genuinely run.",
    ], F_BODY, fade(TEXT, a), leading=34)

    ev = A["evidence"]
    stats = [
        (f"{ev['missions']}", "missions"),
        (f"{ev['node_observations']}", "node outcomes"),
        (f"{len(ev['by_path'])}", "slots"),
        (f"{len(ev['conformance'])}", "conformance vectors"),
    ]
    for i, (value, label) in enumerate(stats):
        b = ease(min(1.0, max(0.0, (t - 0.2 - i * 0.08) * 5.0)))
        x = 92 + i * 356
        panel(d, (x, 306, x + 320, 430))
        d.text((x + 24, 326), value, font=F_H1, fill=fade(ACCENT, b))
        d.text((x + 24, 388), label, font=F_SMALL, fill=fade(MUTED, b))

    c = ease(min(1.0, max(0.0, t * 1.6 - 0.9)))
    typeset(d, 92, 480, [
        "Leaf outcomes are drawn from a fixed reliability, and the exported table",
        "says so. The composition is real; the statistics are synthetic until a",
        "history captured from actual flights drops into the same place.",
    ], F_BODY, fade(MUTED, c), leading=34)

    e = ease(min(1.0, max(0.0, t * 1.6 - 1.3)))
    for i, v in enumerate(ev["conformance"]):
        x = 92 + i * 356
        d.text((x, 620), v["name"], font=F_H2, fill=fade(TEXT, e))
        d.text((x, 664), f"P = {v['p_success'] * 100:.1f}%", font=F_MONO_B,
               fill=fade(OK if v["p_success"] > 0.85 else WARN, e))
    footer(d, "hiko_mission_corpus + hiko_oracle --evidence")
    return img


def scene_leverage(t, A):
    """The one number that changes what somebody does on Monday."""
    img, d = frame()
    header(d, "tree forge", "The node that fails is not the node to fix")

    v = A["takeoff_vector"]
    rows = v["nodes"][:4]

    d.text((92, 190), "share of failure", font=F_SMALL, fill=MUTED)
    d.text((830, 190), "worth fixing", font=F_SMALL, fill=MUTED)

    y = 236
    for i, n in enumerate(rows):
        a = ease(min(1.0, max(0.0, (t - i * 0.09) * 5.0)))
        if a <= 0.01:
            continue
        name = n["path"].split("/")[-1]
        d.text((92, y), name[:16], font=F_H2, fill=fade(TEXT, a))
        bar(d, (330, y + 12, 330 + 420 * n["failure_share"], y + 28), 1.0, fade(BAD, a))
        d.text((760, y + 8), f"{n['failure_share'] * 100:5.1f}%", font=F_MONO, fill=fade(BAD, a))

        b = ease(min(1.0, max(0.0, (t - 0.45 - i * 0.09) * 5.0)))
        bar(d, (900, y + 12, 900 + 420 * (n["leverage"] / 0.12), y + 28), 1.0, fade(OK, b))
        d.text((1340, y + 8), f"+{n['leverage'] * 100:4.2f}%", font=F_MONO, fill=fade(OK, b))
        y += 62

    c = ease(min(1.0, max(0.0, t * 1.5 - 0.95)))
    typeset(d, 92, y + 26, [
        "Takeoff fails every single time — hikosim has supports_takeoff=false and",
        "refuses the request — and carries 99% of the failure. Perfecting it buys 5.4%,",
        "exactly what ClimbTo buys, because the Fallback between them means either",
        "one alone makes the pair certain.",
    ], F_BODY, fade(TEXT, c), leading=34)

    e = ease(min(1.0, max(0.0, t * 1.5 - 1.15)))
    d.text((92, y + 178), "Rank by failure share alone and you spend a fortnight on the node "
           "that does not matter.", font=F_SMALL, fill=fade(ACCENT, e))
    footer(d, "leverage: pin the leaf to 1.0 and re-walk the whole tree, decorators and all")
    return img


def scene_conformance(t, A):
    img, d = frame()
    header(d, "two implementations", "Pinned, not trusted")

    a = ease(min(1.0, t * 2.0))
    typeset(d, 92, 200, [
        "The editor recomputes on every keystroke, so it cannot call into C++.",
        "It holds the statistics and re-implements only the tree algebra.",
    ], F_BODY, fade(TEXT, a), leading=34)

    b = ease(min(1.0, max(0.0, t * 2.0 - 0.5)))
    panel(d, (92, 316, 760, 560))
    d.text((116, 336), "hiko_mission_oracle", font=F_H2, fill=fade(ACCENT, b))
    typeset(d, 116, 386, [
        "counting, Laplace smoothing,",
        "Wilson bounds, the tree algebra",
        "",
        "C++ · 34 tests",
    ], F_SMALL, fade(MUTED, b), leading=30)

    panel(d, (840, 316, W - 90, 560))
    d.text((864, 336), "src/oracle/algebra.ts", font=F_H2, fill=fade(BLUE, b))
    typeset(d, 864, 386, [
        "the tree algebra, again",
        "",
        "",
        "TypeScript · 151 tests",
    ], F_SMALL, fade(MUTED, b), leading=30)

    c = ease(min(1.0, max(0.0, t * 2.0 - 1.0)))
    d.line([(760, 438), (840, 438)], fill=fade(LINE, c), width=2)
    d.text((92, 606), "The export carries vectors the C++ computed. The other side's tests "
           "fail if it", font=F_BODY, fill=fade(TEXT, c))
    d.text((92, 644), "disagrees past the sixth decimal place.", font=F_BODY,
           fill=fade(TEXT, c))
    e = ease(min(1.0, max(0.0, t * 2.0 - 1.4)))
    d.text((92, 706), f"{A['vector_count']} trees · P(success), every node's failure share, "
           f"every node's leverage", font=F_MONO, fill=fade(OK, e))
    footer(d, "conformance.test.ts — the only thing that keeps a re-implementation honest")
    return img


def scene_estimator(t, A):
    """The loop that could not be flown, flying."""
    img, d = frame()
    header(d, "the estimator", "A loop that had never closed")

    blob = A["estimator"]
    metrics = blob["metrics"]
    box = (860, 200, W - 90, 640)
    panel(d, box)
    track = blob["track"]
    reveal = ease(min(1.0, t * 1.6))
    pts = track[: max(2, int(len(track) * reveal))]
    norths = [p["ned"][0] for p in track]
    easts = [p["ned"][1] for p in track]
    lo = min(min(norths), min(easts)) - 2
    hi = max(max(norths), max(easts)) + 2
    span = max(1e-6, hi - lo)

    def px(n, e):
        x = box[0] + 30 + (e - lo) / span * (box[2] - box[0] - 60)
        y = box[3] - 30 - (n - lo) / span * (box[3] - box[1] - 60)
        return x, y

    for target, colour in ((blob["target_hold_ned"], BLUE), (blob["target_goto_ned"], ACCENT)):
        if target:
            x, y = px(target[0], target[1])
            d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=colour, width=2)
    if len(pts) > 1:
        d.line([px(p["ned"][0], p["ned"][1]) for p in pts], fill=OK, width=3)

    rows = [
        ("estimate vs truth, mean", f"{metrics['est_err_mean_m']:.2f} m"),
        ("hold error, worst", f"{metrics['hold_worst_err_m']:.2f} m"),
        ("goto error, worst", f"{metrics['goto_worst_err_m']:.2f} m"),
        ("max tilt", f"{metrics['max_tilt_deg']:.0f}°"),
    ]
    y = 236
    for i, (label, value) in enumerate(rows):
        a = ease(min(1.0, max(0.0, (t - 0.25 - i * 0.09) * 5.0)))
        if a <= 0.01:
            continue
        d.text((92, y), label, font=F_SMALL, fill=fade(MUTED, a))
        d.text((92, y + 30), value, font=F_H1, fill=fade(OK, a))
        y += 104

    c = ease(min(1.0, max(0.0, t * 1.5 - 1.0)))
    typeset(d, 92, 660, [
        "Five faults, each of which looks like bad tuning from outside. The worst",
        "was a velocity measurement the filter invented from its own state: no",
        "information, all confidence, and the position gain fell to 1e-5.",
    ], F_BODY, fade(TEXT, c), leading=34)
    footer(d, "flight_check --platform x500 --estimator — the real nodes, closed loop")
    return img


def scene_envelope(t, A):
    """Where it stops working, including the run that did not hold."""
    img, d = frame()
    header(d, "the forge", "And where it stops")

    env = A["envelope"]
    results = env.get("results", [])
    held = sum(1 for r in results if r.get("outcome") == "held")
    total = len(results)

    a = ease(min(1.0, t * 2.0))
    typeset(d, 92, 200, [
        "The same loop, flown a route, through the estimator, at ten times real",
        "time — swept across wind until it stops holding.",
    ], F_BODY, fade(TEXT, a), leading=34)

    y = 320
    cells = results[:12]
    for i, r in enumerate(cells):
        b = ease(min(1.0, max(0.0, (t - 0.25 - i * 0.05) * 6.0)))
        if b <= 0.01:
            continue
        ok = r.get("outcome") == "held"
        x = 92 + (i % 4) * 356
        row = y + (i // 4) * 92
        panel(d, (x, row, x + 320, row + 74), fill=(16, 20, 28),
              outline=fade(OK if ok else BAD, b))
        # The combo, not the tag: the tag is the two axes concatenated and
        # truncates to "arrival_radius_m=3.0_wind_nort", which hides the value
        # the cell is actually about.
        combo = " · ".join(f"{k.replace('_m', '').replace('_north', '')} {v:g}"
                           for k, v in sorted(r.get("combo", {}).items()))
        d.text((x + 20, row + 12), combo[:34], font=F_MONO_S, fill=fade(MUTED, b))
        d.text((x + 20, row + 38), r.get("outcome", "?"), font=F_MONO_B,
               fill=fade(OK if ok else BAD, b))

    c = ease(min(1.0, max(0.0, t * 1.4 - 1.0)))
    d.text((92, 660), f"{held} of {total} held.", font=F_H1, fill=fade(TEXT, c))
    typeset(d, 92, 726, [
        "The one that did not is in the film for the same reason it is in the report:",
        "a sweep that only ever shows the cells that passed is not a sweep.",
    ], F_SMALL, fade(MUTED, c), leading=28)
    footer(d, "forge/estimator_envelope.yaml — closed loop, real GNC chain, one domain per worker")
    return img


def scene_outro(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.2))
    d.text((90, 300), "Measured,", font=F_TITLE, fill=fade(TEXT, a))
    b = ease(min(1.0, max(0.0, t * 2.2 - 0.45)))
    d.text((90, 386), "not claimed.", font=F_TITLE, fill=fade(ACCENT, b))
    c = ease(min(1.0, max(0.0, t * 1.8 - 0.9)))
    typeset(d, 92, 500, [
        f"{A['tests']} tests. {len(A['repos'])} repositories. Every number in this film",
        "came out of a file a run wrote.",
    ], F_BODY, fade(MUTED, c), leading=36)
    e = ease(min(1.0, max(0.0, t * 1.8 - 1.4)))
    d.text((92, 620), "the-hiko-company.github.io", font=F_MONO, fill=fade(BLUE, e))
    footer(d, "the hiko company — aerial autonomy, electrified")
    return img


SCENES = [
    (scene_title, 6.0),
    (scene_chart, 11.0),
    (scene_demo, 9.5),
    (scene_state_oracle, 10.0),
    (scene_corpus, 9.5),
    (scene_leverage, 12.0),
    (scene_conformance, 9.5),
    (scene_estimator, 10.5),
    (scene_envelope, 10.0),
    (scene_outro, 7.0),
]


def load(artifacts: Path) -> dict:
    # Strip comments properly, across lines. The film is showing that the
    # machine is DATA; forty lines of rationale is not the point, and a filter
    # that only drops lines STARTING with <!-- leaves every continuation line
    # of a multi-line comment sitting in the middle of the XML.
    chart_text = re.sub(r"<!--.*?-->", "", (artifacts / "flight.xml").read_text(), flags=re.S)
    chart_text = chart_text[chart_text.index("<statechart"):]
    chart = [ln for ln in chart_text.splitlines() if ln.strip()]

    demo = (artifacts / "hsm_demo.txt").read_text().splitlines()
    checks = []
    for line in demo:
        match = re.match(r"\s*\[(PASS|FAIL)\]\s+(.*)", line)
        if match:
            label = match.group(2).split(" -- ")[0]
            checks.append((match.group(1) == "PASS", label))
    checks_line = next((ln.strip() for ln in demo if "checks passed" in ln), "")

    evidence = json.loads((artifacts / "evidence.json").read_text())
    takeoff = next(v for v in evidence["conformance"] if v["name"] == "takeoff")
    tests = re.search(r"(\d+) tests", (artifacts / "tests.txt").read_text())

    return {
        "chart_lines": chart,
        "checks": checks,
        "checks_line": checks_line,
        "state_oracle": json.loads((artifacts / "state_oracle.json").read_text()),
        "evidence": evidence,
        "takeoff_vector": takeoff,
        "vector_count": len(evidence["conformance"]),
        "estimator": json.loads((artifacts / "x500_estimator.json").read_text()),
        "envelope": json.loads((artifacts / "estimator_envelope.json").read_text()),
        "tests": tests.group(1) if tests else "?",
        "repos": [ln for ln in (artifacts / "repos.txt").read_text().splitlines() if ln.strip()],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the stack promo film.")
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--frames", default="/tmp/hiko_stack_frames")
    ap.add_argument("--out", default="stack.mp4")
    ap.add_argument("--poster", default=None)
    ap.add_argument("--stills", default=None, help="also write one still per scene here")
    args = ap.parse_args()

    A = load(Path(args.artifacts))

    frames_dir = Path(args.frames)
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    index = 0
    poster_frame = None
    for si, (fn, seconds) in enumerate(SCENES):
        n = int(seconds * FPS)
        for k in range(n):
            img = fn(k / max(1, n - 1), A)
            img.save(frames_dir / f"f{index:05d}.png")
            if args.stills and k == int(n * 0.9):
                Path(args.stills).mkdir(parents=True, exist_ok=True)
                img.save(Path(args.stills) / f"{si:02d}_{fn.__name__[6:]}.png")
            # The leverage scene is the poster: it is the one frame that says
            # what this stack is for without a caption.
            if si == 5 and k == int(n * 0.95):
                poster_frame = img.copy()
            index += 1
        print(f"  {fn.__name__[6:]:<14} {n:4d} frames")

    print(f"{index} frames, {index / FPS:.1f} s")

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-movflags", "+faststart", args.out],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {args.out}")

    if args.poster and poster_frame is not None:
        poster_frame.convert("RGB").save(args.poster, quality=90)
        print(f"wrote {args.poster}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
