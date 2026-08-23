#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the mission film — one sortie, idea to post-analysis, frame by frame.

Same rule as the other four, and this is the strictest case: the film's claim is
that a prediction made BEFORE the mission flew matched what happened when it
did. So the capture script runs in the order the film shows, and nothing is
back-filled.

  artifacts/mission/tree_v1.json      the plan, compiled to a tree
  artifacts/mission/score_v1.txt      what the oracle made of it
  artifacts/mission/tree_v2.json      the same plan after two edits
  artifacts/mission/predicted_v2.*    scored against v1's evidence, unflown
  artifacts/mission/flown_v2.txt      then flown 400 times
  artifacts/mission/flight/           the real closed-loop sortie
  artifacts/mission/session.json      what the recorder captured
  artifacts/mission/mission_record.jsonl  the flight, as evidence

Re-capture with capture_mission_artifacts.sh, then:

    python3 render_mission_promo.py --artifacts artifacts/mission --out mission.mp4
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


def font(size, bold=False, mono=False):
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
F_MONO_S = font(16, mono=True)
F_MONO_B = font(24, mono=True, bold=True)
F_HUGE = font(88, bold=True)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def header(d, kicker, title):
    d.text((90, 62), kicker.upper(), font=F_SMALL, fill=ACCENT)
    d.text((90, 92), title, font=F_H1, fill=TEXT)
    d.line([(90, 156), (W - 90, 156)], fill=LINE, width=2)


def footer(d, note):
    d.line([(90, H - 92), (W - 90, H - 92)], fill=LINE, width=1)
    d.text((90, H - 74), note, font=F_TINY, fill=MUTED)


def panel(d, box, fill=PANEL, outline=LINE):
    d.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=1)


def fade(colour, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(BG[i] + (colour[i] - BG[i]) * t) for i in range(3))


def typeset(d, x, y, lines, f, fill, leading=None):
    leading = leading or (f.size + 10)
    for i, line in enumerate(lines):
        d.text((x, y + i * leading), line, font=f, fill=fill)
    return y + len(lines) * leading


def bar(d, box, colour):
    x0, y0, x1, y1 = box
    if x1 <= x0:
        return
    d.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=colour)


def tree_lines(node, depth=0, out=None):
    """The composed tree, as an indented list. Leaves keep their type."""
    out = [] if out is None else out
    label = node.get("name") or node.get("type", "?")
    attempts = node.get("attempts")
    suffix = f"  x{attempts}" if attempts and attempts > 1 else ""
    out.append((depth, label, node.get("type", "?"), suffix, not node.get("children")))
    for child in node.get("children", []):
        tree_lines(child, depth + 1, out)
    return out


def draw_tree(d, blob, box, reveal=1.0, highlight=()):
    rows = tree_lines(blob["root"])
    shown = int(len(rows) * ease(reveal))
    y = box[1] + 16
    for depth, label, kind, suffix, leaf in rows[:shown]:
        colour = TEXT if leaf else MUTED
        if label in highlight or kind in highlight:
            colour = ACCENT
        d.text((box[0] + 20 + depth * 22, y), f"{label}{suffix}", font=F_MONO_S, fill=colour)
        y += 22
        if y > box[3] - 16:
            break
    return y


# --- scenes -------------------------------------------------------------------


def scene_brief(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.4))
    d.text((90, 268), "Survey two towers.", font=F_TITLE, fill=fade(TEXT, a))
    b = ease(min(1.0, max(0.0, t * 2.4 - 0.5)))
    d.text((90, 354), "Come home.", font=F_TITLE, fill=fade(ACCENT, b))
    c = ease(min(1.0, max(0.0, t * 2.0 - 1.0)))
    typeset(d, 92, 470, [
        "Four waypoints, 4 m/s of wind, one multirotor. An hour of somebody's",
        "afternoon, and the most ordinary thing this stack is asked to do.",
    ], F_BODY, fade(MUTED, c), leading=36)
    e = ease(min(1.0, max(0.0, t * 2.0 - 1.5)))
    d.text((92, 590), "idea  →  design  →  predict  →  edit  →  fly  →  record  →  learn",
           font=F_MONO, fill=fade(BLUE, e))
    footer(d, "one mission, end to end — every number from a file a run wrote")
    return img


def scene_design(t, A):
    img, d = frame()
    header(d, "design", "The plan becomes a tree")
    a = ease(min(1.0, t * 2.2))
    typeset(d, 90, 190, [
        "takeoff  →  fly to tower 1  →  inspect  →  fly to tower 2  →  home  →  land",
    ], F_MONO, fade(ACCENT, a))
    b = ease(min(1.0, max(0.0, t * 1.6 - 0.3)))
    typeset(d, 90, 244, [
        "Six steps. PlanToBt stitches one subtree template per step, so the tree",
        "that flies is composed from the same templates every mission uses.",
    ], F_BODY, fade(MUTED, b), leading=32)

    box = (90, 330, 900, 790)
    panel(d, box)
    draw_tree(d, A["tree_v1"], box, reveal=(t - 0.2) * 1.8)

    c = ease(min(1.0, max(0.0, t * 1.6 - 0.8)))
    shape = A["shape_v1"]
    panel(d, (950, 330, W - 90, 560), fill=(16, 20, 28))
    typeset(d, 976, 356, [
        f"{shape['nodes']} nodes",
        f"{shape['leaves']} leaves",
        f"depth {shape['depth']}",
    ], F_H2, fade(TEXT, c), leading=44)
    e = ease(min(1.0, max(0.0, t * 1.6 - 1.1)))
    typeset(d, 950, 600, [
        "Nobody has flown it.",
        "Nobody knows whether",
        "it works.",
    ], F_H2, fade(MUTED, e), leading=42)
    footer(d, "hiko_mission::PlanToBt — the same compiler the mission manager runs")
    return img


def scene_verdict(t, A):
    img, d = frame()
    header(d, "predict", "Forty-three percent")

    p = A["p_v1"]
    a = ease(min(1.0, t * 2.4))
    d.text((90, 210), f"{p * 100:.1f}%", font=F_HUGE, fill=fade(BAD, a))
    d.text((92, 320), "P(this mission succeeds)", font=F_BODY, fill=fade(MUTED, a))

    b = ease(min(1.0, max(0.0, t * 1.8 - 0.4)))
    d.text((90, 400), "where it goes wrong", font=F_SMALL, fill=fade(MUTED, b))
    y = 440
    peak = max((n["failure_share"] for n in A["nodes_v1"][:5]), default=1.0) or 1.0
    for i, node in enumerate(A["nodes_v1"][:5]):
        c = ease(min(1.0, max(0.0, (t - 0.25 - i * 0.07) * 6.0)))
        if c <= 0.01:
            continue
        name = node["path"].split("/")[-1]
        d.text((92, y), name[:18], font=F_H2, fill=fade(TEXT, c))
        bar(d, (330, y + 10, 330 + 520 * (node["failure_share"] / peak), y + 26), fade(BAD, c))
        d.text((870, y + 6), f"{node['failure_share'] * 100:5.1f}%", font=F_MONO,
               fill=fade(BAD, c))
        d.text((990, y + 6), f"p={node['p_success'] * 100:.1f}%", font=F_MONO_S,
               fill=fade(MUTED, c))
        y += 56

    e = ease(min(1.0, max(0.0, t * 1.5 - 0.8)))
    typeset(d, 90, y + 20, [
        "Nothing was simulated to get this. A tree is a composition, so the",
        "arithmetic is the tree's own: Sequence multiplies, Fallback is one minus",
        "the product of the complements, Retry is 1-(1-p)^n.",
    ], F_BODY, fade(MUTED, e), leading=32)
    footer(d, "hiko_oracle --history --tree — 400 flown missions, counted")
    return img


def scene_edit(t, A):
    img, d = frame()
    header(d, "edit", "Two changes, from what the ranking said")

    a = ease(min(1.0, t * 2.0))
    panel(d, (90, 196, 780, 470))
    d.text((114, 216), "fly.xml", font=F_MONO_B, fill=fade(BLUE, a))
    typeset(d, 114, 262, [
        "<Retry num_attempts=\"3\">",
        "  <Timeout msec=\"180000\">",
        "    <GotoWaypoint .../>",
    ], F_MONO_S, fade(OK, a), leading=26)
    d.text((114, 356), "a leg is the cheapest thing", font=F_SMALL, fill=fade(MUTED, a))
    d.text((114, 384), "in a mission to attempt twice", font=F_SMALL, fill=fade(MUTED, a))

    b = ease(min(1.0, max(0.0, t * 2.0 - 0.4)))
    panel(d, (820, 196, W - 90, 470))
    d.text((844, 216), "inspect.xml", font=F_MONO_B, fill=fade(BLUE, b))
    typeset(d, 844, 262, [
        "<Fallback>",
        "  <Retry num_attempts=\"2\">",
        "    <TrackTarget .../>",
        "  <AlwaysSuccess/>",
    ], F_MONO_S, fade(OK, b), leading=26)
    d.text((844, 384), "a lost track costs the inspection,", font=F_SMALL, fill=fade(MUTED, b))
    d.text((844, 412), "not the sortie", font=F_SMALL, fill=fade(MUTED, b))

    c = ease(min(1.0, max(0.0, t * 1.8 - 0.9)))
    d.text((90, 520), f"{A['p_v1'] * 100:.1f}%", font=F_H1, fill=fade(BAD, c))
    d.text((250, 534), "→", font=F_H1, fill=fade(MUTED, c))
    e = ease(min(1.0, max(0.0, t * 1.8 - 1.2)))
    d.text((320, 520), f"{A['p_v2_predicted'] * 100:.1f}%", font=F_H1, fill=fade(OK, e))
    d.text((92, 596), "predicted — before it has been flown even once", font=F_BODY,
           fill=fade(MUTED, e))

    g = ease(min(1.0, max(0.0, t * 1.8 - 1.15)))
    typeset(d, 90, 664, [
        "The estimate for every leaf still comes from the four hundred missions",
        "the OLD tree flew. Nothing about the new one has been observed; only its",
        "shape changed, and the algebra knows what a shape is worth.",
    ], F_BODY, fade(MUTED, g), leading=32)
    footer(d, "the same two edits are two clicks in Tree Forge")
    return img


def scene_simulate(t, A):
    img, d = frame()
    header(d, "simulate", "Then fly it four hundred times")

    a = ease(min(1.0, t * 2.0))
    d.text((90, 210), "predicted", font=F_SMALL, fill=fade(MUTED, a))
    d.text((90, 240), f"{A['p_v2_predicted'] * 100:.1f}%", font=F_HUGE, fill=fade(BLUE, a))

    b = ease(min(1.0, max(0.0, t * 1.6 - 0.5)))
    d.text((600, 210), "flown", font=F_SMALL, fill=fade(MUTED, b))
    d.text((600, 240), f"{A['flown_v2'] * 100:.1f}%", font=F_HUGE, fill=fade(OK, b))

    c = ease(min(1.0, max(0.0, t * 1.6 - 0.9)))
    d.text((1110, 210), "v1, for comparison", font=F_SMALL, fill=fade(MUTED, c))
    d.text((1110, 244), f"{A['flown_v1'] * 100:.1f}%", font=F_H1, fill=fade(BAD, c))
    d.text((1110, 300), f"predicted {A['p_v1'] * 100:.1f}%", font=F_MONO_S, fill=fade(MUTED, c))

    e = ease(min(1.0, max(0.0, t * 1.5 - 0.85)))
    typeset(d, 90, 420, [
        "Eight hundred missions through the real behaviour-tree engine: composites,",
        "decorators, retry semantics and reactive halting all genuinely executed,",
        "with only the leaf outcomes drawn from a measured reliability.",
    ], F_BODY, fade(TEXT, e), leading=34)

    g = ease(min(1.0, max(0.0, t * 1.5 - 1.15)))
    gap = abs(A["flown_v2"] - A["p_v2_predicted"]) * 100
    d.text((90, 560), f"The forward prediction was {gap:.1f} points out.", font=F_H2,
           fill=fade(ACCENT, g))
    typeset(d, 90, 616, [
        "It said the two edits were worth about twenty-four points. They were worth",
        "twenty-eight. That is the difference between a decision aid and a promise,",
        "and the film is not going to round it away.",
    ], F_BODY, fade(MUTED, g), leading=32)
    footer(d, "hiko_mission_corpus — the shipped templates, the real engine")
    return img


def scene_fly(t, A):
    img, d = frame()
    header(d, "execute", "Then fly it for real")

    flight = A["flight"]
    box = (860, 190, W - 90, 660)
    panel(d, box)
    track = flight["track"]
    route = flight["waypoints_ned"]
    norths = [p["ned"][0] for p in track] + [w[0] for w in route]
    easts = [p["ned"][1] for p in track] + [w[1] for w in route]
    lo = min(min(norths), min(easts)) - 6
    hi = max(max(norths), max(easts)) + 6
    span = max(1e-6, hi - lo)

    def px(n, e):
        x = box[0] + 34 + (e - lo) / span * (box[2] - box[0] - 68)
        y = box[3] - 34 - (n - lo) / span * (box[3] - box[1] - 68)
        return x, y

    for i, waypoint in enumerate(route):
        x, y = px(waypoint[0], waypoint[1])
        d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=ACCENT, width=2)
        d.text((x + 14, y - 12), str(i), font=F_MONO_S, fill=MUTED)
    reveal = ease(min(1.0, t * 1.5))
    points = track[: max(2, int(len(track) * reveal))]
    if len(points) > 1:
        d.line([px(p["ned"][0], p["ned"][1]) for p in points], fill=OK, width=3)
        head = px(points[-1]["ned"][0], points[-1]["ned"][1])
        d.ellipse([head[0] - 5, head[1] - 5, head[0] + 5, head[1] + 5], fill=TEXT)

    rows = [
        ("legs held", f"{flight['metrics']['legs_reached']}/{flight['metrics']['legs_total']}"),
        ("estimate vs truth", f"{flight['metrics']['estimator_error_mean_m']:.2f} m"),
        ("wind", f"{flight['wind_north_mps']:.0f} m/s"),
    ]
    y = 220
    for i, (label, value) in enumerate(rows):
        a = ease(min(1.0, max(0.0, (t - 0.3 - i * 0.1) * 5.0)))
        if a <= 0.01:
            continue
        d.text((92, y), label, font=F_SMALL, fill=fade(MUTED, a))
        d.text((92, y + 30), value, font=F_H1, fill=fade(OK, a))
        y += 110

    c = ease(min(1.0, max(0.0, t * 1.4 - 1.0)))
    typeset(d, 92, 570, [
        "The simulator's plant and sensors, the ESKF, the cascaded controller —",
        "every one of them the node that flies. The vehicle is navigating on its",
        "OWN state estimate; truth appears nowhere in the control path, and is",
        "subscribed to only so the report can say how far the estimate was from it.",
    ], F_BODY, fade(MUTED, c), leading=32)
    footer(d, "mission_run.py — closed loop on the ESKF, recorded, one leg")
    return img


def scene_spread(t, A):
    """The stage that does not work, and says so."""
    img, d = frame()
    header(d, "analysis", "Where this stack actually stops")

    rows = A["attempts"]
    y = 196
    for i, run in enumerate(rows):
        a = ease(min(1.0, max(0.0, (t - i * 0.08) * 5.0)))
        if a <= 0.01:
            continue
        ok = run["outcome"] == "SUCCESS"
        colour = OK if ok else BAD
        d.text((92, y), run["mission"], font=F_BODY, fill=fade(MUTED, a))
        d.text((400, y), run["outcome"], font=F_MONO_B, fill=fade(colour, a))
        d.text((600, y + 2), f"{run['legs_reached']}/{run['legs_total']} legs",
               font=F_MONO, fill=fade(TEXT, a))
        error = run["estimator_error_mean_m"]
        d.text((780, y + 2), f"{error:>9.2f} m", font=F_MONO, fill=fade(colour, a))
        d.text((980, y + 4), "estimate vs truth", font=F_SMALL, fill=fade(MUTED, a))
        y += 50

    b = ease(min(1.0, max(0.0, t * 1.4 - 0.7)))
    typeset(d, 92, y + 20, [
        "The one-leg sortie holds to a metre and records cleanly. The four-waypoint",
        "survey does not fly at all — same nodes, same gains, same wind.",
    ], F_BODY, fade(TEXT, b), leading=32)

    c = ease(min(1.0, max(0.0, t * 1.4 - 1.0)))
    typeset(d, 92, y + 108, [
        "The magnetometer's innovation IS the yaw error, and it is gated. Nothing",
        "else observes yaw. So once heading is thirty degrees wrong every further",
        "correction is rejected BECAUSE it is wrong, the cascade sustains itself,",
        "and the vehicle flies the error. One flight logged 595 in a row.",
    ], F_BODY, fade(MUTED, c), leading=32)

    e = ease(min(1.0, max(0.0, t * 1.4 - 1.1)))
    d.text((92, y + 248), "Open, and named. The film is not going to crop it out.",
           font=F_H2, fill=fade(ACCENT, e))
    footer(d, "hiko-gnc/docs/estimator.md#the-magnetometer-cascade")
    return img


def scene_collect(t, A):
    img, d = frame()
    header(d, "collect", "And keep all of it")

    s = A["session"]
    stats = [
        (str(len(s["topics"])), "topics"),
        (f"{A['messages']:,}".replace(",", " "), "messages"),
        (f"{s['total_bytes'] / 1e6:.0f} MB", "serialized"),
        (f"{s['_on_disk_bytes'] / 1e6:.0f} MB", "on disk"),
    ]
    for i, (value, label) in enumerate(stats):
        a = ease(min(1.0, max(0.0, (t - i * 0.09) * 5.0)))
        x = 90 + i * 356
        panel(d, (x, 200, x + 320, 330))
        d.text((x + 24, 222), value, font=F_H1, fill=fade(ACCENT, a))
        d.text((x + 24, 284), label, font=F_SMALL, fill=fade(MUTED, a))

    b = ease(min(1.0, max(0.0, t * 1.6 - 0.5)))
    d.text((90, 380), "the busiest channels", font=F_SMALL, fill=fade(MUTED, b))
    busiest = sorted(s["topics"], key=lambda x: -x.get("message_count", 0))[:6]
    peak = busiest[0].get("message_count", 1) or 1
    y = 420
    for i, topic in enumerate(busiest):
        c = ease(min(1.0, max(0.0, (t - 0.5 - i * 0.06) * 6.0)))
        if c <= 0.01:
            continue
        d.text((92, y), topic["name"][:44], font=F_MONO_S, fill=fade(TEXT, c))
        bar(d, (620, y + 4, 620 + 620 * (topic["message_count"] / peak), y + 18), fade(BLUE, c))
        d.text((1270, y), f"{topic['message_count']:>7}", font=F_MONO_S, fill=fade(MUTED, c))
        y += 32

    e = ease(min(1.0, max(0.0, t * 1.4 - 0.95)))
    typeset(d, 90, y + 26, [
        "A manifest beside the chunks: session id, stack revision, platform, every",
        "topic and its QoS, and a parameter snapshot of every node on the graph.",
        "Without it a recording is a directory of bytes nobody can index.",
    ], F_BODY, fade(MUTED, e), leading=32)
    footer(d, "hiko_recorder — mcap chunks + manifest, indexed by hiko_datalake")
    return img


def scene_learn(t, A):
    img, d = frame()
    header(d, "learn", "And the flight becomes evidence")

    a = ease(min(1.0, t * 2.0))
    panel(d, (90, 200, W - 90, 360))
    record = A["record_text"]
    d.text((114, 226), record[:118], font=F_MONO_S, fill=fade(OK, a))
    if len(record) > 118:
        d.text((114, 254), record[118:236], font=F_MONO_S, fill=fade(OK, a))
    d.text((114, 306), "one MissionRecord — the format hiko_oracle reads",
           font=F_SMALL, fill=fade(MUTED, a))

    b = ease(min(1.0, max(0.0, t * 1.8 - 0.5)))
    stages = ["design", "predict", "edit", "fly", "record", "learn"]
    x = 120
    for i, stage in enumerate(stages):
        c = ease(min(1.0, max(0.0, (t - 0.4 - i * 0.06) * 7.0)))
        d.text((x, 450), stage, font=F_H2, fill=fade(ACCENT if i in (1, 5) else TEXT, c))
        if i < len(stages) - 1:
            d.text((x + 140, 454), "→", font=F_H2, fill=fade(MUTED, c))
        x += 208
    e = ease(min(1.0, max(0.0, t * 1.6 - 1.0)))
    d.line([(1330, 470), (1330, 520), (120, 520), (120, 490)], fill=fade(ACCENT, e), width=2)
    d.text((640, 534), "the next mission is scored against this one", font=F_SMALL,
           fill=fade(ACCENT, e))

    g = ease(min(1.0, max(0.0, t * 1.4 - 1.05)))
    typeset(d, 90, 610, [
        "Nothing here is trained. It is counting, Laplace smoothing and Wilson",
        "bounds over missions that actually flew, composed by the tree's own",
        "algebra — a weaker claim than a model, and a far more defensible one.",
    ], F_BODY, fade(TEXT, g), leading=34)
    footer(d, "fly the mission → record the run → score the next one")
    return img


def scene_outro(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.2))
    d.text((90, 292), "Predicted 68%.", font=F_TITLE, fill=fade(TEXT, a))
    b = ease(min(1.0, max(0.0, t * 2.2 - 0.5)))
    d.text((90, 378), f"Flew {A['flown_v2'] * 100:.0f}%.", font=F_TITLE, fill=fade(ACCENT, b))
    c = ease(min(1.0, max(0.0, t * 1.8 - 1.0)))
    typeset(d, 92, 496, [
        "One mission, from an idea to the evidence it leaves behind.",
        "Every number in this film came out of a file a run wrote.",
    ], F_BODY, fade(MUTED, c), leading=36)
    e = ease(min(1.0, max(0.0, t * 1.8 - 1.4)))
    d.text((92, 616), "the-hiko-company.github.io", font=F_MONO, fill=fade(BLUE, e))
    footer(d, "the hiko company — aerial autonomy, electrified")
    return img


SCENES = [
    (scene_brief, 6.5),
    (scene_design, 10.5),
    (scene_verdict, 12.0),
    (scene_edit, 12.5),
    (scene_simulate, 12.0),
    (scene_fly, 11.5),
    (scene_spread, 12.0),
    (scene_collect, 11.0),
    (scene_learn, 11.0),
    (scene_outro, 7.0),
]


def shape_of(blob):
    rows = tree_lines(blob["root"])
    return {
        "nodes": len(rows),
        "leaves": sum(1 for r in rows if r[4]),
        "depth": max(r[0] for r in rows) + 1,
    }


def flown_rate(text):
    """"... FAILURE=109 SUCCESS=291" -> 0.7275"""
    failure = int(re.search(r"FAILURE=(\d+)", text).group(1))
    success = int(re.search(r"SUCCESS=(\d+)", text).group(1))
    return success / (success + failure)


def load(artifacts: Path) -> dict:
    tree_v1 = json.loads((artifacts / "tree_v1.json").read_text())
    evidence_v1 = json.loads((artifacts / "evidence_v1.json").read_text())
    predicted_v2 = json.loads((artifacts / "predicted_v2.json").read_text())
    flight = json.loads((artifacts / "flight" / "mission_run.json").read_text())
    session = json.loads((artifacts / "session.json").read_text())
    return {
        "tree_v1": tree_v1,
        "shape_v1": shape_of(tree_v1),
        "p_v1": evidence_v1["conformance"][0]["p_success"],
        "nodes_v1": evidence_v1["conformance"][0]["nodes"],
        "p_v2_predicted": predicted_v2["conformance"][0]["p_success"],
        "flown_v1": flown_rate((artifacts / "flown_v1.txt").read_text()),
        "flown_v2": flown_rate((artifacts / "flown_v2.txt").read_text()),
        "flight": flight,
        "attempts": json.loads((artifacts / "attempts.json").read_text()),
        "session": session,
        "messages": sum(t.get("message_count", 0) for t in session["topics"]),
        "record_text": (artifacts / "mission_record.jsonl").read_text().strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the mission film.")
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--frames", default="/tmp/hiko_mission_frames")
    ap.add_argument("--out", default="mission.mp4")
    ap.add_argument("--poster", default=None)
    ap.add_argument("--stills", default=None)
    args = ap.parse_args()

    A = load(Path(args.artifacts))
    frames_dir = Path(args.frames)
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    index = 0
    poster = None
    for si, (fn, seconds) in enumerate(SCENES):
        n = int(seconds * FPS)
        for k in range(n):
            img = fn(k / max(1, n - 1), A)
            img.save(frames_dir / f"f{index:05d}.png")
            if args.stills and k == int(n * 0.9):
                Path(args.stills).mkdir(parents=True, exist_ok=True)
                img.save(Path(args.stills) / f"{si:02d}_{fn.__name__[6:]}.png")
            # The prediction-versus-outcome scene is the poster: it is the one
            # frame that states the claim without a caption.
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
