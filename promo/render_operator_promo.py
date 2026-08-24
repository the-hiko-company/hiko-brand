#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the operator film — design, score, push, fly, measure.

Same rule as the other five: EVERYTHING ON SCREEN IS A REAL ARTEFACT. Every
number, every node, every point on the altitude trace is read from
artifacts/operator/run.json and control.json, written by
hiko-gcs/tools/operator_flight_demo.py against the simulator, the estimator, the
controller and the mission manager.

Including the part that does not work. The aircraft is asked for 25 m and does
not get there, and the film says so, because a promo that cut the failing check
would be a promo about a different product.

    python3 render_operator_promo.py --out hiko-operator.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts" / "operator"

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


def font(size, bold=False, mono=False):
    if mono:
        name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    else:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font(66, bold=True)
F_H1 = font(40, bold=True)
F_H2 = font(26, bold=True)
F_BODY = font(23)
F_SMALL = font(19)
F_TINY = font(16)
F_MONO = font(19, mono=True)
F_MONO_S = font(15, mono=True)
F_MONO_B = font(23, mono=True, bold=True)
F_HUGE = font(92, bold=True)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def fade(colour, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(BG[i] + (colour[i] - BG[i]) * t) for i in range(3))


def header(d, kicker, title, t=1.0):
    d.text((90, 62), kicker.upper(), font=F_SMALL, fill=fade(ACCENT, t))
    d.text((90, 92), title, font=F_H1, fill=fade(TEXT, t))
    d.line([(90, 152), (W - 90, 152)], fill=fade(LINE, t), width=2)


def footer(d, note, t=1.0):
    d.line([(90, H - 90), (W - 90, H - 90)], fill=fade(LINE, t), width=1)
    d.text((90, H - 72), note, font=F_TINY, fill=fade(MUTED, t))


def panel(d, box, t=1.0):
    d.rounded_rectangle(box, radius=10, fill=fade(PANEL, t), outline=fade(LINE, t), width=1)


RUN = json.loads((ART / "run.json").read_text())
CONTROL = (json.loads((ART / "control.json").read_text())["trace"]
           if (ART / "control.json").exists() else [])
VERDICT = RUN["verdict"]
BLAME = json.loads(VERDICT["verdict_json"])["blame"]
CHECKS = RUN["checks"]
TRANS = RUN.get("transitions", [])
KIND = {0: "", 1: "INTENDED", 2: "FAULT", 3: "TIMEOUT"}


def node_rows():
    """Per-node metrics, exactly as the console's panel computes them."""
    rows = {}
    for tr in TRANS:
        path = tr["path"]
        leaf = path.split("/")[-1]
        row = rows.setdefault(leaf, {"path": path, "ok": 0, "fail": 0, "halt": 0,
                                     "secs": 0.0, "type": tr.get("type", ""), "kind": 0})
        to, frm = tr.get("to_status", 0), tr.get("from_status", 0)
        if frm == 1:
            row["secs"] += tr.get("duration_s", 0.0)
            if to == 0:
                row["halt"] += 1
        if to == 2:
            row["ok"] += 1
        if to == 3:
            row["fail"] += 1
            row["kind"] = tr.get("failure_kind", 0)
    paths = [r["path"] for r in rows.values()]
    return {k: v for k, v in rows.items()
            if not any(p != v["path"] and p.startswith(v["path"] + "/") for p in paths)}


ROWS = node_rows()


def scene_title(d, t):
    a = ease(t * 2.2)
    d.text((90, 330), "THE OPERATOR LOOP", font=F_TITLE, fill=fade(TEXT, a))
    b = ease((t - 0.18) * 2.2)
    d.text((92, 425), "design  ·  score  ·  push  ·  fly  ·  measure",
           font=F_H2, fill=fade(ACCENT, b))
    c = ease((t - 0.38) * 2.0)
    d.text((92, 500),
           "One run against the simulator, the estimator, the controller\n"
           "and the mission manager. Every number below came out of it.",
           font=F_BODY, fill=fade(MUTED, c), spacing=12)
    e = ease((t - 0.72) * 3.0)
    d.text((90, H - 130), "HIKO STACK", font=F_SMALL, fill=fade(ACCENT, e))


def scene_tree(d, t):
    header(d, "on board", "The mission the aircraft is flying", ease(t * 3))
    panel(d, (90, 190, W - 90, H - 130), ease(t * 3))
    d.text((120, 215), "every leaf the console saw run, and what it did",
           font=F_SMALL, fill=fade(MUTED, ease(t * 3)))
    y = 268
    for i, (leaf, row) in enumerate(list(ROWS.items())[:9]):
        a = ease((t - 0.12 - i * 0.05) * 4.0)
        if a <= 0:
            continue
        state = OK if row["ok"] and not row["fail"] else (BAD if row["fail"] else MUTED)
        d.rounded_rectangle((120, y, 370, y + 42), radius=6, outline=fade(state, a), width=2)
        d.text((136, y + 10), leaf[:22], font=F_MONO, fill=fade(TEXT, a))
        d.text((400, y + 12), row["type"][:18], font=F_SMALL, fill=fade(MUTED, a))
        mark = "SUCCESS" if row["ok"] and not row["fail"] else ("FAILURE" if row["fail"] else "-")
        d.text((610, y + 12), mark, font=F_SMALL, fill=fade(state, a))
        if row["fail"] and KIND.get(row["kind"]):
            d.text((740, y + 12), KIND[row["kind"]], font=F_SMALL, fill=fade(WARN, a))
        d.text((900, y + 12), f"{row['secs']:.2f} s", font=F_MONO_S, fill=fade(MUTED, a))
        y += 52
    footer(d, "/hiko/autonomy/bt/transitions - one message per status CHANGE, not per tick",
           ease((t - 0.5) * 3))


def scene_verdict(d, t):
    header(d, "before anyone takes off", "Rehearsed on the vehicle", ease(t * 3))
    a = ease((t - 0.08) * 3.0)
    panel(d, (90, 190, 760, 470), a)
    d.text((120, 215), "P(MISSION SUCCEEDS)", font=F_SMALL, fill=fade(MUTED, a))
    grow = ease((t - 0.15) * 2.2)
    d.text((120, 250), f"{VERDICT['p_success'] * grow * 100:.1f}%", font=F_HUGE,
           fill=fade(ACCENT, a))
    d.text((120, 370),
           f"{VERDICT['p_low'] * 100:.1f}-{VERDICT['p_high'] * 100:.1f}% at 95%, "
           f"over {VERDICT['runs_done']} executed runs", font=F_SMALL, fill=fade(MUTED, a))
    d.text((120, 405), "the real tree, real composites, real decorators",
           font=F_TINY, fill=fade(MUTED, a))

    b = ease((t - 0.3) * 3.0)
    panel(d, (800, 190, W - 90, 470), b)
    d.text((830, 212), "WHERE THE MISSION TURNS", font=F_SMALL, fill=fade(MUTED, b))
    y = 250
    for i, entry in enumerate(BLAME):
        c = ease((t - 0.38 - i * 0.07) * 4.0)
        if c <= 0:
            continue
        leaf = entry["path"].split("/")[-1][:20]
        if entry["withheld"]:
            d.text((830, y), "-", font=F_MONO_B, fill=fade(BLUE, c))
            d.text((890, y + 3), leaf, font=F_MONO, fill=fade(MUTED, c))
            d.text((890, y + 28), "withheld: never succeeded", font=F_TINY, fill=fade(BLUE, c))
            y += 62
        elif entry["share"] > 0.005:
            d.text((830, y), f"{entry['share'] * 100:4.0f}%", font=F_MONO_B, fill=fade(ACCENT, c))
            d.text((930, y + 3), leaf, font=F_MONO, fill=fade(TEXT, c))
            y += 42
    late = ease((t - 0.7) * 3)
    d.text((830, 420), "a node that never succeeds says nothing about",
           font=F_TINY, fill=fade(MUTED, late))
    d.text((830, 442), "what its success would be worth", font=F_TINY, fill=fade(MUTED, late))
    footer(d, VERDICT["caveat"][:118], ease((t - 0.6) * 3))


def scene_push(d, t):
    header(d, "over the console's own link", "Pushed, between ticks", ease(t * 3))
    steps = [("set_blackboard", f"climb_to = {RUN['target_m']:.0f} m"),
             ("load_tree", f"accepted - {RUN['node_count']} nodes"),
             ("tree_source", "the aircraft reports what it is running")]
    y = 250
    for i, (call, detail) in enumerate(steps):
        a = ease((t - 0.1 - i * 0.17) * 3.2)
        if a <= 0:
            continue
        panel(d, (90, y, W - 90, y + 110), a)
        d.text((124, y + 24), f">  {call}", font=F_MONO_B, fill=fade(BLUE, a))
        d.text((124, y + 62), detail, font=F_BODY, fill=fade(TEXT, a))
        d.ellipse((W - 160, y + 42, W - 132, y + 70), fill=fade(OK, a))
        y += 140
    footer(d, "a malformed tree is refused without disturbing what is flying",
           ease((t - 0.75) * 3))


def _box():
    return 150, W - 110, 230, H - 190


def _scales():
    xs = [p[0] for p in RUN["trace"]] + [p[0] for p in CONTROL]
    ys = [p[1] for p in RUN["trace"]] + [p[1] for p in CONTROL] + [RUN["target_m"]]
    return max(xs or [1]), max(ys or [1])


def _pt(ts, alt, tmax, amax):
    x0, x1, y0, y1 = _box()
    return (x0 + (ts / tmax) * (x1 - x0), y1 - (max(alt, 0.0) / amax) * (y1 - y0))


def scene_fly(d, t):
    header(d, "the aircraft", "What it actually did", ease(t * 3))
    tmax, amax = _scales()
    x0, x1, y0, y1 = _box()
    a = ease(t * 3)
    for m in range(0, int(amax) + 1, 5):
        _, yy = _pt(0, m, tmax, amax)
        d.line([(x0, yy), (x1, yy)], fill=fade(LINE, a), width=1)
        d.text((x0 - 46, yy - 11), f"{m:>2}", font=F_MONO_S, fill=fade(MUTED, a))
    _, ty = _pt(0, RUN["target_m"], tmax, amax)
    d.line([(x0, ty), (x1, ty)], fill=fade(ACCENT, a), width=2)
    d.text((x1 - 330, ty - 30), f"{RUN['target_m']:.0f} m - what the operator asked for",
           font=F_SMALL, fill=fade(ACCENT, a))

    cutoff = ease((t - 0.1) * 1.5) * tmax
    ctl = [_pt(ts, al, tmax, amax) for ts, al in CONTROL if ts <= cutoff]
    run = [_pt(ts, al, tmax, amax) for ts, al in RUN["trace"] if ts <= cutoff]
    if len(ctl) > 1:
        d.line(ctl, fill=fade(MUTED, 0.55), width=2)
    if len(run) > 1:
        d.line(run, fill=fade(TEXT, 1.0), width=4)
    for ts, label in RUN["events"]:
        if label != "pushed" or ts > cutoff:
            continue
        px, _ = _pt(ts, 0, tmax, amax)
        d.line([(px, y0), (px, y1)], fill=ACCENT, width=3)
        d.text((px + 10, y0 + 4), "tree pushed", font=F_SMALL, fill=ACCENT)
    late = ease((t - 0.72) * 3.0)
    d.text((x0, y1 + 26), "- with the pushed tree", font=F_SMALL, fill=fade(TEXT, late))
    d.text((x0 + 300, y1 + 26), "- control run, nothing pushed",
           font=F_SMALL, fill=fade(MUTED, late))
    footer(d, "simulator truth, not the estimator: this is about the command path",
           ease((t - 0.4) * 3))


def scene_honest(d, t):
    header(d, "what this proves", "And what it does not", ease(t * 3))
    a = ease((t - 0.05) * 3.0)
    panel(d, (90, 190, 780, 520), a)
    d.text((120, 214), "PROVEN", font=F_SMALL, fill=fade(OK, a))
    d.text((120, 252),
           "A plan rehearsed on the vehicle.\n"
           "A parameter set from the ground.\n"
           "A tree pushed and accepted between ticks.\n"
           "The aircraft reporting the tree it runs.\n"
           "Every node's outcome and timing, live.",
           font=F_BODY, fill=fade(TEXT, a), spacing=14)
    b = ease((t - 0.3) * 3.0)
    panel(d, (820, 190, W - 90, 520), b)
    d.text((850, 214), "NOT PROVEN", font=F_SMALL, fill=fade(BAD, b))
    d.text((850, 252),
           f"It was asked for {RUN['target_m']:.0f} m and reached\n"
           f"{RUN['reached_m']:.1f} m. This airframe starts\n"
           "descending about ten seconds after\n"
           "the hover - the estimator defect in\n"
           "hiko-gnc/docs/estimator.md.\n"
           "The control run falls the same way,\n"
           "so it is not the push.",
           font=F_BODY, fill=fade(TEXT, b), spacing=14)
    c = ease((t - 0.62) * 3.0)
    passed = sum(1 for x in CHECKS if x["ok"])
    d.text((90, 570), f"{passed} of {len(CHECKS)} checks passed", font=F_H2, fill=fade(TEXT, c))
    d.text((90, 614),
           "An earlier cut of this demo asked only for \"higher than it was\", and passed on\n"
           "the scenario's own takeoff. It was green and it meant nothing.",
           font=F_SMALL, fill=fade(MUTED, c), spacing=10)
    footer(d, "hiko demo c2.operator_flight - every number here came out of one run",
           ease((t - 0.8) * 3))


SCENES = [(scene_title, 6.0), (scene_tree, 8.0), (scene_verdict, 9.0),
          (scene_push, 7.0), (scene_fly, 9.0), (scene_honest, 9.5)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "hiko-operator.mp4"))
    ap.add_argument("--poster")
    ap.add_argument("--frames", default="/tmp/hiko_operator_frames")
    args = ap.parse_args()

    frames_dir = Path(args.frames)
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    index, poster = 0, None
    for si, (fn, seconds) in enumerate(SCENES):
        n = int(seconds * FPS)
        for k in range(n):
            img, d = frame()
            fn(d, k / max(n - 1, 1))
            img.save(frames_dir / f"f{index:05d}.png")
            if si == 4 and k == int(n * 0.95):
                poster = img.copy()
            index += 1
        print(f"  {fn.__name__[6:]:<10} {n:4d} frames")
    print(f"{index} frames, {index / FPS:.1f} s")

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-movflags", "+faststart", args.out],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {args.out}")
    if args.poster and poster is not None:
        poster.convert("RGB").save(args.poster, quality=90)
        print(f"wrote {args.poster}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
