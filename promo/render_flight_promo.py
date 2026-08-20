#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the platforms & flight promo film, frame by frame.

Same rule as the other two films, and it is why this script reads files instead
of drawing shapes: EVERYTHING ON SCREEN IS A REAL ARTEFACT.

  artifacts/flight/platforms/*.yaml   the shipped catalogue, verbatim
  artifacts/flight/x500.json          a real closed-loop run, hikosim
  artifacts/flight/quadplane.json     ditto
  artifacts/flight/talon.json         ditto
  artifacts/flight/x500_gazebo.json   the same loop through Gazebo's ODE solver

Every track drawn is the vehicle's actual position over time, and every figure
quoted is a metric the check computed. There is no path through this script that
draws an invented number.

Re-capture with capture_flight_artifacts.sh, then:

    python3 render_flight_promo.py --artifacts artifacts/flight --out flight.mp4

Pillow for frames, ffmpeg for encoding. No motion-graphics toolchain.
"""

from __future__ import annotations

import argparse
import json
import math
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
ACCENT = (245, 197, 24)      # lightning yellow
OK = (126, 217, 87)
WARN = (255, 180, 84)
BAD = (255, 107, 107)

# One colour per airframe class, used everywhere the class appears so the eye
# can follow one vehicle across scenes without reading a label again.
CLASS_COLOUR = {
    "multirotor": (108, 196, 255),
    "vtol": (196, 152, 255),
    "fixed_wing": (255, 176, 118),
}


def font(size: int, bold: bool = False, mono: bool = False):
    if mono:
        name = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
    else:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font(64, bold=True)
F_H1 = font(42, bold=True)
F_H2 = font(30, bold=True)
F_BODY = font(24)
F_SMALL = font(20)
F_TINY = font(17)
F_MONO = font(20, mono=True)
F_MONO_S = font(16, mono=True)
F_MONO_B = font(22, mono=True, bold=True)


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
    """Toward the background, for reveals."""
    t = max(0.0, min(1.0, t))
    return tuple(int(BG[i] + (colour[i] - BG[i]) * t) for i in range(3))


def typeset(d, x, y, lines, f, fill, leading=None):
    leading = leading or (f.size + 10)
    for i, line in enumerate(lines):
        d.text((x, y + i * leading), line, font=f, fill=fill)
    return y + len(lines) * leading


# --- plotting the real tracks -------------------------------------------------
#
# North is UP and east is RIGHT, which is the only orientation a reader will
# assume without being told. Getting this wrong once put every overlay in the
# wrong place on the nav film, so it is written down and used everywhere.

class Track:
    """A captured flight, projected into a box."""

    def __init__(self, blob: dict, box, pad=0.12):
        self.blob = blob
        self.box = box
        self.pts = [s["ned"] for s in blob["track"]]
        self.ts = [s["t"] for s in blob["track"]]
        norths = [p[0] for p in self.pts]
        easts = [p[1] for p in self.pts]
        # Include the commanded targets in the extent: a plot that crops the
        # setpoint out cannot show whether the vehicle reached it.
        for key in ("target_hold_ned", "target_goto_ned"):
            tgt = blob.get(key)
            if tgt:
                norths.append(tgt[0])
                easts.append(tgt[1])
        span = max(max(norths) - min(norths), max(easts) - min(easts), 1.0)
        span *= 1.0 + pad
        self.cn = (max(norths) + min(norths)) / 2.0
        self.ce = (max(easts) + min(easts)) / 2.0
        self.span = span
        x0, y0, x1, y1 = box
        self.scale = min(x1 - x0, y1 - y0) / span
        self.mx = (x0 + x1) / 2.0
        self.my = (y0 + y1) / 2.0

    def px(self, north, east):
        return (self.mx + (east - self.ce) * self.scale,
                self.my - (north - self.cn) * self.scale)

    def draw_plan(self, d, colour, reveal=1.0, width=3):
        n = max(2, int(len(self.pts) * max(0.02, reveal)))
        pts = [self.px(p[0], p[1]) for p in self.pts[:n]]
        if len(pts) > 1:
            d.line(pts, fill=colour, width=width, joint="curve")
        return pts[-1] if pts else None

    def draw_targets(self, d):
        for key, label in (("target_hold_ned", "hold"), ("target_goto_ned", "goto")):
            tgt = self.blob.get(key)
            if not tgt:
                continue
            x, y = self.px(tgt[0], tgt[1])
            d.line([(x - 9, y), (x + 9, y)], fill=ACCENT, width=2)
            d.line([(x, y - 9), (x, y + 9)], fill=ACCENT, width=2)
            d.text((x + 12, y - 10), label, font=F_TINY, fill=ACCENT)


def alt_plot(d, blob, box, colour, reveal=1.0, target=None):
    """Altitude against time. NED down is negative, so altitude is -down."""
    x0, y0, x1, y1 = box
    panel(d, box)
    ts = [s["t"] for s in blob["track"]]
    alts = [-s["ned"][2] for s in blob["track"]]
    lo, hi = min(alts), max(alts)
    if target is not None:
        lo, hi = min(lo, target), max(hi, target)
    pad = max(1.0, (hi - lo) * 0.2)
    lo, hi = lo - pad, hi + pad
    tmax = max(ts) or 1.0

    def px(t, a):
        return (x0 + 14 + (t / tmax) * (x1 - x0 - 28),
                y1 - 14 - ((a - lo) / (hi - lo)) * (y1 - y0 - 28))

    if target is not None:
        ya = px(0, target)[1]
        for x in range(int(x0 + 14), int(x1 - 14), 12):
            d.line([(x, ya), (x + 6, ya)], fill=ACCENT, width=1)
    n = max(2, int(len(ts) * max(0.02, reveal)))
    pts = [px(ts[i], alts[i]) for i in range(n)]
    if len(pts) > 1:
        d.line(pts, fill=colour, width=3, joint="curve")
    d.text((x0 + 14, y0 + 10), "altitude", font=F_TINY, fill=MUTED)
    d.text((x1 - 90, y0 + 10), f"{hi - pad:.0f} m", font=F_TINY, fill=MUTED)


def yaml_field(text: str, key: str, default="—"):
    """The one field this film needs out of a platform YAML.

    A real parser would be better and would also be a dependency; the catalogue
    files are flat at the top level and this only ever reads scalars from them.
    """
    for line in text.splitlines():
        line = line.split("#")[0].rstrip()
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return default


def yaml_count(text: str, key: str) -> int:
    """How many entries a top-level sequence has."""
    inside = False
    n = 0
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip()
        if not line:
            continue
        if line.startswith(key + ":"):
            inside = True
            continue
        if inside:
            if line.startswith("  - "):
                n += 1
            elif not line.startswith("  "):
                break
    return n


# --- scenes -------------------------------------------------------------------

def scene_title(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.4))
    d.text((90, 300), "Three airframes.", font=F_TITLE, fill=fade(TEXT, a))
    b = ease(min(1.0, max(0.0, t * 2.4 - 0.5)))
    d.text((90, 386), "One definition.", font=F_TITLE, fill=fade(ACCENT, b))
    c = ease(min(1.0, max(0.0, t * 2.0 - 1.0)))
    typeset(d, 92, 500, [
        "A multirotor, a fixed wing and a VTOL, flown closed-loop through the",
        "same controller — and told apart by one line of configuration.",
    ], F_BODY, fade(MUTED, c), leading=36)
    footer(d, "hiko_platform · hiko_controllers · hikosim · Gazebo Classic")
    return img


def scene_problem(t, A):
    img, d = frame()
    header(d, "before", "A platform lived in four places")
    rows = [
        ("hikosim model YAML", "mass, rotor coefficients"),
        ("hiko-gnc mixer", "arm length, thrust per rotor"),
        ("hiko_multimodal", "capabilities, cruise speed"),
        ("hiko-nav", "footprint — hardcoded 0.5 m for everything"),
    ]
    y = 220
    for i, (where, what) in enumerate(rows):
        a = ease(min(1.0, max(0.0, t * 3.2 - i * 0.35)))
        panel(d, (110, y, 900, y + 78), fill=fade(PANEL, a))
        d.text((136, y + 14), where, font=F_H2, fill=fade(TEXT, a))
        d.text((136, y + 48), what, font=F_SMALL, fill=fade(MUTED, a))
        y += 96

    a = ease(min(1.0, max(0.0, t * 2.6 - 1.1)))
    typeset(d, 950, 236, [
        "Adding an airframe meant",
        "editing four files in three",
        "repositories.",
    ], F_H2, fade(TEXT, a), leading=42)
    b = ease(min(1.0, max(0.0, t * 2.6 - 1.5)))
    typeset(d, 950, 400, [
        "Miss one and you get a vehicle",
        "that flies with the wrong inertia,",
        "or plans with the wrong footprint.",
        "",
        "Both entirely plausible-looking.",
    ], F_BODY, fade(MUTED, b), leading=34)
    footer(d, "the failure mode the catalogue exists to remove")
    return img


def scene_catalogue(t, A):
    img, d = frame()
    header(d, "hiko_platform", "The catalogue: read by everything")
    order = [("x500", "multirotor"), ("talon", "fixed_wing"), ("quadplane", "vtol")]
    x = 110
    for i, (pid, cls) in enumerate(order):
        a = ease(min(1.0, max(0.0, t * 2.6 - i * 0.4)))
        y = json_ = A["platforms"].get(pid, "")
        col = CLASS_COLOUR[cls]
        panel(d, (x, 210, x + 440, 700), fill=fade(PANEL, a))
        d.rounded_rectangle((x, 210, x + 440, 216), radius=3, fill=fade(col, a))
        d.text((x + 28, 238), pid, font=F_H1, fill=fade(TEXT, a))
        d.text((x + 28, 292), cls.replace("_", " ").upper(), font=F_SMALL, fill=fade(col, a))
        fields = [
            ("mass", yaml_field(json_, "mass_kg") + " kg"),
            ("lift rotors", str(yaml_count(json_, "rotors"))),
            ("surfaces", str(yaml_count(json_, "surfaces"))),
            ("cruise", yaml_field(json_, "  cruise_speed_m_s")),
            ("stall", yaml_field(json_, "  min_speed_m_s")),
            ("footprint", yaml_field(json_, "  radius_m") + " m"),
            ("floor AGL", yaml_field(json_, "  min_altitude_agl_m") + " m"),
        ]
        yy = 348
        for k, v in fields:
            d.text((x + 28, yy), k, font=F_SMALL, fill=fade(MUTED, a))
            d.text((x + 250, yy), v, font=F_MONO, fill=fade(TEXT, a))
            yy += 42
        x += 460

    a = ease(min(1.0, max(0.0, t * 2.4 - 1.2)))
    d.text((110, 726), "one file per vehicle · validated at load · naming an unknown id is refused",
           font=F_BODY, fill=fade(ACCENT, a))
    footer(d, "fields read verbatim from the shipped platforms/*.yaml")
    return img


def flight_scene(pid, kicker, title, notes, footnote, reveal_from=0.0):
    def render(t, A):
        img, d = frame()
        header(d, kicker, title)
        blob = A["flights"][pid]
        col = CLASS_COLOUR[blob["class"]]
        r = ease(min(1.0, max(0.0, (t - reveal_from) * 1.5)))

        box = (110, 200, 760, 760)
        panel(d, box)
        tr = Track(blob, (130, 220, 740, 740))
        tr.draw_targets(d)
        tip = tr.draw_plan(d, col, reveal=r)
        if tip:
            d.ellipse([tip[0] - 7, tip[1] - 7, tip[0] + 7, tip[1] + 7], fill=col)
        d.text((130, 208), "ground track — north up, east right", font=F_TINY, fill=MUTED)

        target_alt = -blob["target_hold_ned"][2] if blob.get("target_hold_ned") else None
        alt_plot(d, blob, (800, 200, 1490, 430), col, reveal=r, target=target_alt)

        m = blob["metrics"]
        y = 470
        for i, (label, value, colour) in enumerate(notes(m)):
            a = ease(min(1.0, max(0.0, t * 2.2 - 0.7 - i * 0.22)))
            panel(d, (800, y, 1490, y + 66), fill=fade(PANEL, a))
            d.text((824, y + 20), label, font=F_SMALL, fill=fade(MUTED, a))
            d.text((1180, y + 14), value, font=F_MONO_B, fill=fade(colour, a))
            y += 78
        footer(d, footnote)
        return img
    return render


def scene_x500(t, A):
    return flight_scene(
        "x500", "flown · multirotor", "Hold a point, then move to another",
        lambda m: [
            ("hold, worst error", f"{m['hold_worst_err_m']:.2f} m", OK),
            ("translate, worst error", f"{m['goto_worst_err_m']:.2f} m", OK),
            ("peak tilt", f"{m['max_tilt_deg']:.0f}°", TEXT),
            ("actuator commands", f"{m['actuator_commands']:,}", MUTED),
        ],
        "arriving is not enough — the check asserts it is STILL there six seconds later",
    )(t, A)


def scene_quadplane(t, A):
    return flight_scene(
        "quadplane", "flown · vtol", "The airframe that breaks one-actuator assumptions",
        lambda m: [
            ("hold, worst error", f"{m['hold_worst_err_m']:.2f} m", OK),
            ("translate, worst error", f"{m['goto_worst_err_m']:.2f} m", OK),
            ("peak tilt", f"{m['max_tilt_deg']:.0f}°", TEXT),
            ("actuator commands", f"{m['actuator_commands']:,}", MUTED),
        ],
        "kMixed has no wire representation — it goes out as two messages, motors then servos",
    )(t, A)


def scene_talon(t, A):
    return flight_scene(
        "talon", "flown · fixed wing", "A wing cannot hold a point. It can hold energy.",
        lambda m: [
            ("altitude, worst error", f"{m['alt_worst_err_m']:.2f} m", OK),
            ("minimum speed", f"{m['min_speed_m_s']:.1f} m/s", OK),
            ("closest approach", f"{m['closest_approach_m']:.1f} m", OK),
            ("peak bank", f"{m['max_bank_deg']:.0f}°", TEXT),
        ],
        "stall is 11.0 m/s — the check asserts airspeed, altitude AND that it actually banked",
    )(t, A)


def scene_tecs(t, A):
    img, d = frame()
    header(d, "why", "A wing needed a law the stack did not have")
    a = ease(min(1.0, t * 2.4))
    typeset(d, 110, 214, [
        "Handed a position setpoint, the multirotor cascade put the talon into a steady",
        "13-degree nose-down attitude and flew it into the ground — with every gain",
        "reasonable and every message well formed.",
    ], F_BODY, fade(TEXT, a), leading=36)

    b = ease(min(1.0, max(0.0, t * 2.2 - 0.7)))
    typeset(d, 110, 344, [
        "Position error → desired acceleration → thrust VECTOR → tilt is correct for a",
        "multirotor and structurally wrong for a wing, where pitch does not point the",
        "thrust: it trades speed for height. And all four guidance laws are lateral.",
    ], F_BODY, fade(MUTED, b), leading=36)

    c = ease(min(1.0, max(0.0, t * 2.4 - 0.85)))
    panel(d, (110, 486, 740, 742), fill=fade(PANEL, c))
    d.text((140, 508), "THROTTLE", font=F_H2, fill=fade(ACCENT, c))
    typeset(d, 140, 552, ["moves the TOTAL energy", "— climbing and accelerating",
                          "  both cost power"], F_BODY, fade(TEXT, c), leading=34)
    panel(d, (770, 486, 1400, 742), fill=fade(PANEL, c))
    d.text((800, 508), "PITCH", font=F_H2, fill=fade(ACCENT, c))
    typeset(d, 800, 552, ["moves the BALANCE",
                          "— nose-up buys height by",
                          "  spending speed"], F_BODY, fade(TEXT, c), leading=34)

    e = ease(min(1.0, max(0.0, t * 2.4 - 1.5)))
    d.text((110, 766), "height and airspeed are two views of one energy budget",
           font=F_BODY, fill=fade(ACCENT, e))
    footer(d, "hiko_controllers/FixedWingController — TECS + coordinated-turn bank law")
    return img


def scene_two_sims(t, A):
    img, d = frame()
    header(d, "verification", "The same loop, a different solver")
    sims = [
        ("hikosim", A["flights"]["x500"], "in-house rigid body"),
        ("Gazebo Classic", A["gazebo"], "ODE, contact, real inertia"),
    ]
    x = 110
    for i, (name, blob, sub) in enumerate(sims):
        a = ease(min(1.0, max(0.0, t * 2.4 - i * 0.4)))
        panel(d, (x, 200, x + 660, 620), fill=fade(PANEL, a))
        d.text((x + 28, 220), name, font=F_H2, fill=fade(TEXT, a))
        d.text((x + 28, 258), sub, font=F_SMALL, fill=fade(MUTED, a))
        tr = Track(blob, (x + 40, 300, x + 620, 600))
        tr.draw_targets(d)
        tr.draw_plan(d, fade(CLASS_COLOUR["multirotor"], a), reveal=ease(min(1.0, t * 1.6)))
        m = blob["metrics"]
        d.text((x + 28, 604 - 300), "", font=F_TINY, fill=MUTED)
        x += 680

    b = ease(min(1.0, max(0.0, t * 2.6 - 1.0)))
    y = 646
    left = A["flights"]["x500"]["metrics"]
    right = A["gazebo"]["metrics"]
    rows = [
        ("hold, worst error", f"{left['hold_worst_err_m']:.2f} m", f"{right['hold_worst_err_m']:.2f} m"),
        ("translate, worst error", f"{left['goto_worst_err_m']:.2f} m", f"{right['goto_worst_err_m']:.2f} m"),
    ]
    for label, l, r in rows:
        d.text((110, y), label, font=F_SMALL, fill=fade(MUTED, b))
        d.text((600, y - 4), l, font=F_MONO_B, fill=fade(OK, b))
        d.text((1180, y - 4), r, font=F_MONO_B, fill=fade(OK, b))
        y += 44
    c = ease(min(1.0, max(0.0, t * 2.4 - 1.4)))
    d.text((110, 754), "same controller, same mixer, same gains file — only the physics changes",
           font=F_BODY, fill=fade(ACCENT, c))
    footer(d, "a difference in the result would be a difference in the physics, not the plumbing")
    return img


def scene_tiers(t, A):
    img, d = frame()
    header(d, "how it stays true", "Three tiers, three questions")
    tiers = [
        ("unit", "is the algorithm right?", "no ROS · microseconds", TEXT),
        ("component", "is it wired right?", "real node, real graph, no physics · milliseconds",
         CLASS_COLOUR["multirotor"]),
        ("system", "does it fly?", "full physics · tens of seconds", ACCENT),
    ]
    y = 214
    for i, (name, q, how, col) in enumerate(tiers):
        a = ease(min(1.0, max(0.0, t * 2.6 - i * 0.42)))
        panel(d, (110, y, 1100, y + 148), fill=fade(PANEL, a))
        d.rounded_rectangle((110, y, 116, y + 148), radius=3, fill=fade(col, a))
        d.text((146, y + 22), name, font=F_H1, fill=fade(col, a))
        d.text((146, y + 82), q, font=F_H2, fill=fade(TEXT, a))
        d.text((146, y + 118), how, font=F_SMALL, fill=fade(MUTED, a))
        y += 168

    b = ease(min(1.0, max(0.0, t * 2.4 - 0.9)))
    panel(d, (1140, 214, 1490, 704), fill=fade(PANEL, b))
    d.text((1174, 244), "1250", font=F_TITLE, fill=fade(ACCENT, b))
    d.text((1174, 318), "tests, 0 failures", font=F_SMALL, fill=fade(MUTED, b))
    d.line([(1174, 372), (1456, 372)], fill=LINE, width=1)
    typeset(d, 1174, 396, [
        "65 packages",
        "9 repositories",
        "4 nodes covered",
        "at the component tier",
    ], F_BODY, fade(TEXT, b), leading=36)
    d.text((1174, 566), "and the same", font=F_SMALL, fill=fade(MUTED, b))
    d.text((1174, 594), "1250 pass inside", font=F_SMALL, fill=fade(MUTED, b))
    d.text((1174, 622), "a pinned, rootless", font=F_SMALL, fill=fade(MUTED, b))
    d.text((1174, 650), "environment", font=F_SMALL, fill=fade(MUTED, b))
    footer(d, "a tier nobody waits for is a tier that runs on every commit")
    return img


def scene_outro(t, A):
    img, d = frame()
    a = ease(min(1.0, t * 2.2))
    d.text((90, 286), "One argument changes", font=F_TITLE, fill=fade(TEXT, a))
    d.text((90, 366), "the vehicle.", font=F_TITLE, fill=fade(ACCENT, a))
    b = ease(min(1.0, max(0.0, t * 2.0 - 0.6)))
    lines = [
        "ros2 launch hiko_scenarios platform_demo.launch.py platform:=x500",
        "ros2 launch hiko_scenarios platform_demo.launch.py platform:=talon",
        "ros2 launch hiko_scenarios platform_demo.launch.py platform:=quadplane",
    ]
    panel(d, (90, 470, 1180, 636), fill=fade(PANEL, b))
    typeset(d, 118, 494, lines, F_MONO_S, fade(TEXT, b), leading=44)
    c = ease(min(1.0, max(0.0, t * 2.4 - 1.1)))
    d.text((90, 676), "the simulator's mass and rotors, the navigation footprint, the mixer",
           font=F_BODY, fill=fade(MUTED, c))
    d.text((90, 710), "and the Gazebo world all resolve from the same file.",
           font=F_BODY, fill=fade(MUTED, c))
    footer(d, "THE HIKO COMPANY · aerial autonomy, electrified")
    return img


SCENES = [
    (scene_title, 5.0),
    (scene_problem, 9.0),
    (scene_catalogue, 9.5),
    (scene_x500, 8.5),
    (scene_quadplane, 8.5),
    (scene_talon, 9.0),
    (scene_tecs, 10.0),
    (scene_two_sims, 9.5),
    (scene_tiers, 9.0),
    (scene_outro, 7.0),
]


def load(artifacts: Path) -> dict:
    flights = {}
    for pid in ("x500", "quadplane", "talon"):
        flights[pid] = json.loads((artifacts / f"{pid}.json").read_text())
    platforms = {}
    for pid in ("x500", "quadplane", "talon"):
        platforms[pid] = (artifacts / "platforms" / f"{pid}.yaml").read_text()
    return {
        "flights": flights,
        "gazebo": json.loads((artifacts / "x500_gazebo.json").read_text()),
        "platforms": platforms,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the platforms & flight promo film.")
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--frames", default="/tmp/hiko_flight_frames")
    ap.add_argument("--out", default="flight.mp4")
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
            if args.stills and k == int(n * 0.85):
                Path(args.stills).mkdir(parents=True, exist_ok=True)
                img.save(Path(args.stills) / f"{si:02d}_{fn.__name__[6:]}.png")
            # The talon scene is the poster: it is the one frame that says
            # "this is not another quadrotor demo" without a caption.
            if poster_frame is None and si == 5 and k == int(n * 0.9):
                poster_frame = img.copy()
            index += 1
        print(f"  {fn.__name__[6:]:<12} {n:4d} frames")

    total = index / FPS
    print(f"{index} frames, {total:.1f} s")

    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
           "-movflags", "+faststart", args.out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {args.out}")

    if args.poster and poster_frame is not None:
        poster_frame.convert("RGB").save(args.poster, quality=90)
        print(f"wrote {args.poster}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
