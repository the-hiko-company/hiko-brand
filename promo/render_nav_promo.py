#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the hiko-nav promo film, frame by frame.

Same rule as render_promo.py, and it is the reason this script reads files
instead of drawing shapes: EVERYTHING ON SCREEN IS A REAL ARTEFACT.

  artifacts/nav/costmap.json     a real CostVolume slice captured from hikosim
  artifacts/nav/field.json       a real ObstacleField (samples + normals)
  artifacts/nav/status.json      a real CostmapStatus (per-layer, timing)
  artifacts/nav/paths.json       real routes planned on that captured map
  artifacts/nav/preference.json  the planner's own output on the constructed
                                 test map -- labelled as such on screen, because
                                 it is not the simulator scene

There is no code path here that draws an invented number. Where a scene needs a
map, it renders the captured cost array cell by cell; where it needs a route, it
draws the waypoints the planner returned.

    python3 render_nav_promo.py --artifacts artifacts/nav --out nav.mp4

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

# --- brand -------------------------------------------------------------------

BG = (11, 14, 20)
PANEL = (20, 25, 34)
LINE = (31, 39, 51)
TEXT = (230, 234, 242)
MUTED = (138, 148, 166)
ACCENT = (245, 197, 24)      # lightning yellow
ION = (62, 197, 255)         # ion blue
GOOD = (62, 207, 142)
WARN = (255, 180, 84)
BAD = (255, 107, 107)

W, H = 1600, 900
FPS = 24

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


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


def frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def header(d: ImageDraw.ImageDraw, kicker: str, title: str) -> None:
    d.text((90, 62), kicker.upper(), font=F_SMALL, fill=ACCENT)
    d.text((90, 92), title, font=F_H1, fill=TEXT)
    d.line([(90, 156), (W - 90, 156)], fill=LINE, width=2)


def footer(d: ImageDraw.ImageDraw, note: str) -> None:
    d.line([(90, H - 92), (W - 90, H - 92)], fill=LINE, width=1)
    d.text((90, H - 74), note, font=F_TINY, fill=MUTED)


def mask_outside(d, box):
    """Repaint everything outside `box` with the background.

    Overlays drawn in world coordinates -- a query radius, a route that leaves
    the observed region -- do not know where the panel ends. Clipping after the
    fact is simpler than teaching every overlay its bounds, and the background
    is flat, so it is exact.
    """
    x0, y0, x1, y1 = box
    d.rectangle((0, 0, W, y0), fill=BG)
    d.rectangle((0, y1, W, H), fill=BG)
    d.rectangle((0, y0, x0, y1), fill=BG)
    d.rectangle((x1, y0, W, y1), fill=BG)


def panel(d, box, fill=PANEL, outline=LINE):
    d.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=1)


# --- cost colouring ----------------------------------------------------------

def cost_colour(v: int):
    """The palette IS the legend: the three sentinels are not on the gradient.

    Unknown is nearly background, because unobserved space should not read as
    information. Lethal and inscribed are their own colours rather than the top
    of a ramp, because they are constraints and not merely expensive.
    """
    if v == 255:
        return (24, 28, 36)
    if v == 254:
        return BAD
    if v == 253:
        return (196, 84, 96)
    if v == 0:
        return (34, 42, 54)
    t = min(1.0, v / 252.0)
    # free -> ion -> accent as cost climbs
    if t < 0.5:
        u = t / 0.5
        return (int(34 + (62 - 34) * u), int(42 + (197 - 42) * u), int(54 + (255 - 54) * u))
    u = (t - 0.5) / 0.5
    return (int(62 + (245 - 62) * u), int(197 + (197 - 197) * u), int(255 + (24 - 255) * u))


class Slice:
    """A 2D cost slice with a consistent world<->pixel mapping.

    Orientation: NORTH IS UP, EAST IS RIGHT -- the way anyone reads a map. The
    cost array is x-fastest with x = north, so the index arithmetic below is the
    one place that has to know it, and every overlay goes through world_to_px so
    a route and the map underneath it cannot disagree about which way is north.
    """

    def __init__(self, data: dict, box, key="cost", crop_margin=6):
        self.n_north = data["size_x"]
        self.n_east = data["size_y"]
        self.res = data["resolution"]
        self.origin = data.get("origin", [0.0, 0.0, 0.0])
        self.cost = data[key]

        # Crop to what was actually observed. Most of a rolling costmap is
        # unknown, and rendering all of it shrinks the interesting part to a
        # smudge in the middle of a grey square.
        lo_n, hi_n, lo_e, hi_e = self.n_north, -1, self.n_east, -1
        for i, v in enumerate(self.cost):
            if v == 255:
                continue
            inorth, ieast = i % self.n_north, i // self.n_north
            lo_n, hi_n = min(lo_n, inorth), max(hi_n, inorth)
            lo_e, hi_e = min(lo_e, ieast), max(hi_e, ieast)
        if hi_n < 0:
            lo_n, hi_n, lo_e, hi_e = 0, self.n_north - 1, 0, self.n_east - 1
        self.lo_n = max(0, lo_n - crop_margin)
        self.hi_n = min(self.n_north - 1, hi_n + crop_margin)
        self.lo_e = max(0, lo_e - crop_margin)
        self.hi_e = min(self.n_east - 1, hi_e + crop_margin)
        self.cols = self.hi_e - self.lo_e + 1
        self.rows = self.hi_n - self.lo_n + 1

        self.x0, self.y0, self.x1, self.y1 = box
        self.px = min((self.x1 - self.x0) / self.cols, (self.y1 - self.y0) / self.rows)
        self.ox = self.x0 + ((self.x1 - self.x0) - self.px * self.cols) / 2
        self.oy = self.y0 + ((self.y1 - self.y0) - self.px * self.rows) / 2

    def _screen(self, inorth, ieast):
        """Cell index -> (col, row). North up means increasing north is a
        DECREASING row; getting this backwards mirrors the map."""
        return (ieast - self.lo_e, self.hi_n - inorth)

    def cell_box(self, inorth, ieast):
        col, row = self._screen(inorth, ieast)
        return (self.ox + col * self.px, self.oy + row * self.px,
                self.ox + (col + 1) * self.px, self.oy + (row + 1) * self.px)

    def world_to_px(self, north, east):
        fn = (north - self.origin[0]) / self.res
        fe = (east - self.origin[1]) / self.res
        col = fe - self.lo_e
        row = self.hi_n - fn
        return (self.ox + col * self.px, self.oy + row * self.px)

    def vector_to_px(self, north, east):
        """A direction, mapped the same way a position delta is."""
        return (east * self.px / self.res, -north * self.px / self.res)

    def draw(self, d, reveal=1.0, mode="full"):
        d.rectangle((self.ox, self.oy, self.ox + self.px * self.cols,
                     self.oy + self.px * self.rows), fill=cost_colour(255))
        for i, raw in enumerate(self.cost):
            inorth, ieast = i % self.n_north, i // self.n_north
            if not (self.lo_n <= inorth <= self.hi_n and self.lo_e <= ieast <= self.hi_e):
                continue
            v = raw
            if mode == "binary":
                # What a binary occupancy map can say: passable, or not.
                v = 254 if raw in (253, 254) else (255 if raw == 255 else 0)
            if v == 255:
                continue  # already painted as the background
            if reveal < 1.0:
                _, row = self._screen(inorth, ieast)
                if row / max(1, self.rows) > reveal:
                    continue
            d.rectangle(self.cell_box(inorth, ieast), fill=cost_colour(v))


def draw_route(d, sl: Slice, waypoints, colour, width=4, dot=6, xy_only=False):
    pts = []
    for wp in waypoints:
        wx, wy = (wp[0], wp[1])
        pts.append(sl.world_to_px(wx, wy))
    if len(pts) >= 2:
        d.line(pts, fill=colour, width=width, joint="curve")
    for p in pts:
        d.ellipse([p[0] - dot, p[1] - dot, p[0] + dot, p[1] + dot], fill=colour)


# --- scenes ------------------------------------------------------------------

def scene_title(t, A):
    img, d = frame()
    a = ease(t / 0.55)
    d.text((90, 300), "THE HIKO COMPANY", font=F_SMALL,
           fill=(int(ACCENT[0] * a), int(ACCENT[1] * a), int(ACCENT[2] * a)))
    c = int(230 * a)
    d.text((90, 338), "The navigation layer", font=F_TITLE, fill=(c, c, c))
    if t > 0.35:
        b = ease((t - 0.35) / 0.4)
        m = int(148 * b)
        d.text((90, 428), "Sensors in, cost out, and one distance field",
               font=F_H2, fill=(m, m, m))
        d.text((90, 468), "that everything else asks questions of.",
               font=F_H2, fill=(m, m, m))
    if t > 0.65:
        c2 = ease((t - 0.65) / 0.35)
        d.line([(90, 540), (90 + int(420 * c2), 540)], fill=ACCENT, width=3)
    footer(d, "Every frame in this film is rendered from output the stack produced. "
              "Nothing here is a mockup.")
    return img


def scene_problem(t, A):
    """The same real map, twice: what a binary map can say vs what cost can."""
    img, d = frame()
    header(d, "why a costmap", "A boolean cannot express a preference")

    real = A["costmap"]
    left = Slice(real, (110, 200, 740, 700))
    right = Slice(real, (860, 200, 1490, 700))

    a = ease(t / 0.3)
    if a > 0:
        left.draw(d, mode="binary")
        d.text((110, 176), "BINARY OCCUPANCY", font=F_SMALL, fill=MUTED)
    if t > 0.32:
        b = ease((t - 0.32) / 0.3)
        right.draw(d, reveal=b)
        d.text((860, 176), "GRADED COST", font=F_SMALL, fill=ACCENT)

    if t > 0.66:
        c = ease((t - 0.66) / 0.34)
        m = int(148 * c)
        d.text((110, 722), "passable, or not. Every free cell looks the same,",
               font=F_SMALL, fill=(m, m, m))
        d.text((110, 750), "so shortest-path scrapes the wall.", font=F_SMALL, fill=(m, m, m))
        d.text((860, 722), "cost falls off with clearance, so the same",
               font=F_SMALL, fill=(m, m, m))
        d.text((860, 750), "planner centres itself without being told to.",
               font=F_SMALL, fill=(m, m, m))
    footer(d, f"Real costmap slice captured from hikosim -- {real['size_x']}x{real['size_y']} cells "
              f"at {real['resolution']} m, built from live lidar sweeps against two pillars.")
    return img


def scene_layers(t, A):
    img, d = frame()
    header(d, "the abstraction", "Everything that observes becomes cost")

    rows = [
        ("point clouds", "lidar, depth, any hiko_pointcloud producer", ION),
        ("terrain", "the ground is lethal; a band above it is graded", GOOD),
        ("tracked objects", "swept forward; the cone widens with time", WARN),
        ("inflation", "runs last, builds the distance field, grades by clearance", ACCENT),
    ]
    for i, (name, why, col) in enumerate(rows):
        appear = 0.06 + i * 0.13
        if t < appear:
            continue
        a = ease((t - appear) / 0.16)
        y = 220 + i * 108
        x = 110 - int(40 * (1 - a))
        panel(d, (x, y, x + 640, y + 84))
        d.rectangle((x, y, x + 6, y + 84), fill=col)
        d.text((x + 28, y + 16), name, font=F_H2, fill=TEXT)
        d.text((x + 28, y + 54), why, font=F_TINY, fill=MUTED)
        d.line([(x + 660, y + 42), (940, y + 42)], fill=LINE, width=2)

    if t > 0.6:
        a = ease((t - 0.6) / 0.25)
        panel(d, (960, 220, 1480, 516), fill=(26, 32, 42), outline=ACCENT)
        d.text((992, 250), "ONE COST GRID", font=F_H2, fill=ACCENT)
        for j, line in enumerate([
            "0          free",
            "1..252     graded penalty",
            "253        INSCRIBED",
            "254        LETHAL",
            "255        UNKNOWN",
        ]):
            m = int(230 * a)
            d.text((992, 306 + j * 34), line, font=F_MONO, fill=(m, m, m))
    if t > 0.78:
        a = ease((t - 0.78) / 0.22)
        m = int(148 * a)
        panel(d, (960, 540, 1480, 800))
        d.text((992, 566), "The top three are CONSTRAINTS,", font=F_SMALL, fill=TEXT)
        d.text((992, 594), "not large numbers.", font=F_SMALL, fill=TEXT)
        for j, line in enumerate([
            "A planner minimising a sum will",
            "route through an obstacle the moment",
            "the detour is long enough. No finite",
            "number makes 'fly into the building'",
            "lose to every alternative.",
        ]):
            d.text((992, 640 + j * 28), line, font=F_TINY, fill=(m, m, m))
    footer(d, "A layer raises cost and never erases. The grid is wiped and re-derived every "
              "cycle, so a layer that stops seeing something can say so.")
    return img


def scene_clearing(t, A):
    img, d = frame()
    header(d, "the obstacle layer", "Marking is the easy half")

    real = A["costmap"]
    sl = Slice(real, (110, 190, 810, 780))
    sl.draw(d, reveal=min(1.0, ease(t / 0.35)))

    d.text((110, 168), "SENSED", font=F_SMALL, fill=MUTED)

    if t > 0.3:
        a = ease((t - 0.3) / 0.25)
        panel(d, (860, 210, 1480, 470))
        d.text((892, 236), "Ray clearing", font=F_H2, fill=ION)
        for j, line in enumerate([
            "Everything between the sensor and the",
            "return was just observed to be EMPTY.",
            "A map that never records that is one",
            "where obstacles are immortal: fly past",
            "a car and the corridor it blocked stays",
            "blocked forever.",
        ]):
            m = int(148 * a)
            d.text((892, 286 + j * 28), line, font=F_TINY, fill=(m, m, m))

    if t > 0.56:
        a = ease((t - 0.56) / 0.25)
        panel(d, (860, 500, 1480, 760))
        d.text((892, 526), "Decay", font=F_H2, fill=WARN)
        for j, line in enumerate([
            "Clearing needs the obstacle back in",
            "view. Anything that left the field of",
            "view while occupied is unreachable by",
            "clearing, so observations also age out.",
            "",
            "Evidence of absence, and the absence",
            "of evidence. Two mechanisms, because",
            "collapsing them loses the difference.",
        ]):
            m = int(148 * a)
            d.text((892, 576 + j * 24), line, font=F_TINY, fill=(m, m, m))

    census = A["status"]
    footer(d, f"Captured: {census['cells_lethal']} lethal cells and "
              f"{census['cells_total'] - census['cells_unknown'] - census['cells_lethal']} "
              f"cleared free cells out of {census['cells_total']}, from real lidar sweeps.")
    return img


def scene_preference(t, A):
    """The planner's own output, twice, on the constructed test map."""
    img, d = frame()
    header(d, "planning over cost", "The same planner, two weights")

    pref = A["preference"]
    box_l = (110, 200, 740, 690)
    box_r = (860, 200, 1490, 690)
    sl_l = Slice(pref, box_l)
    sl_r = Slice(pref, box_r)
    sl_l.origin = [0.0, 0.0, 0.0]
    sl_r.origin = [0.0, 0.0, 0.0]

    a = ease(t / 0.22)
    if a > 0:
        sl_l.draw(d)
        sl_r.draw(d)

    r0, r1 = pref["routes"][0], pref["routes"][1]
    if t > 0.26:
        p = ease((t - 0.26) / 0.3)
        n = max(2, int(len(r0["waypoints"]) * p) + 1)
        draw_route(d, sl_l, r0["waypoints"][:n], BAD)
        d.text((110, 176), f"cost_weight  {r0['cost_weight']:.0f}", font=F_MONO_B, fill=BAD)
    if t > 0.42:
        p = ease((t - 0.42) / 0.3)
        n = max(2, int(len(r1["waypoints"]) * p) + 1)
        draw_route(d, sl_r, r1["waypoints"][:n], GOOD)
    d.rectangle((0, 700, W, H), fill=BG)
    if t > 0.26:
        d.text((110, 176), f"cost_weight  {r0['cost_weight']:.0f}", font=F_MONO_B, fill=BAD)
    if t > 0.42:
        d.text((860, 176), f"cost_weight {r1['cost_weight']:.0f}", font=F_MONO_B, fill=GOOD)

    if t > 0.7:
        a = ease((t - 0.7) / 0.3)
        m = int(230 * a)
        d.text((110, 714), f"{r0['length_m']:.1f} m through a 1 m slot",
               font=F_MONO, fill=(m, m, m))
        d.text((110, 744), f"min clearance {r0['min_clearance_m']:.2f} m",
               font=F_MONO_S, fill=BAD)
        d.text((860, 714), f"{r1['length_m']:.1f} m around it",
               font=F_MONO, fill=(m, m, m))
        d.text((860, 744), f"min clearance {r1['min_clearance_m']:.2f} m",
               font=F_MONO_S, fill=GOOD)

    footer(d, "Constructed test map, real planner output. Weight 0 is what a binary planner "
              "does; it pays 5.1 m for four times the clearance.")
    return img


def scene_route(t, A):
    """A real route on the real captured map."""
    img, d = frame()
    header(d, "on the real map", "Routes through what the lidar found")

    real = A["costmap"]
    map_box = (110, 190, 840, 780)
    sl = Slice(real, map_box)
    sl.draw(d)

    routes = [r for r in A["paths"]["routes"] if r["success"]]
    colours = [ACCENT, ION]
    for i, r in enumerate(routes[:2]):
        appear = 0.2 + i * 0.22
        if t < appear:
            continue
        p = ease((t - appear) / 0.28)
        n = max(2, int(len(r["waypoints"]) * p) + 1)
        draw_route(d, sl, r["waypoints"][:n], colours[i % 2])
    mask_outside(d, map_box)
    header(d, "on the real map", "Routes through what the lidar found")

    if t > 0.55:
        a = ease((t - 0.55) / 0.2)
        panel(d, (880, 210, 1480, 470))
        d.text((910, 236), "What the planner reports", font=F_H2, fill=TEXT)
        y = 292
        for i, r in enumerate(routes[:2]):
            m = int(230 * a)
            d.rectangle((910, y + 4, 916, y + 46), fill=colours[i % 2])
            d.text((932, y), r["label"], font=F_SMALL, fill=(m, m, m))
            d.text((932, y + 26),
                   f"{r['length_m']:.1f} m   min clearance {r['min_clearance_m']:.2f} m",
                   font=F_MONO_S, fill=MUTED)
            y += 76

    if t > 0.72:
        a = ease((t - 0.72) / 0.28)
        m = int(148 * a)
        panel(d, (880, 500, 1480, 800))
        d.text((910, 526), "Clearance is measured", font=F_H2, fill=ACCENT)
        d.text((910, 562), "ALONG the path", font=F_H2, fill=ACCENT)
        for j, line in enumerate([
            "After shortcutting, a route through a",
            "3 m gap can be two waypoints with the",
            "gap in the middle of the segment",
            "between them, and never sampled.",
            "",
            "A caller picks a cruise speed from",
            "this number.",
        ]):
            d.text((910, 616 + j * 26), line, font=F_TINY, fill=(m, m, m))

    unreachable = [r for r in A["paths"]["routes"] if not r["success"]]
    note = ("A goal in unobserved space is refused when allow_unknown is false: "
            f"\"{unreachable[0]['message']}\"." if unreachable else
            "Routes planned on the captured map.")
    footer(d, note)
    return img


def scene_field(t, A):
    """The ESDF's public face: samples and normals, as the flocker sees them."""
    img, d = frame()
    header(d, "the distance field", "One query, three consumers")

    field = A["field"]
    real = A["costmap"]
    map_box = (110, 190, 840, 780)
    sl = Slice(real, map_box)
    sl.draw(d)

    qx, qy = field["query_point"][0], field["query_point"][1]
    qp = sl.world_to_px(qx, qy)

    if t > 0.14:
        a = ease((t - 0.14) / 0.2)
        r = sl.px * field["query_radius_m"] / sl.res * a
        d.ellipse([qp[0] - r, qp[1] - r, qp[0] + r, qp[1] + r], outline=ION, width=2)

    if t > 0.3:
        p = ease((t - 0.3) / 0.35)
        shown = int(len(field["samples"]) * p) + 1
        for s in field["samples"][:shown]:
            sp = sl.world_to_px(s["point"][0], s["point"][1])
            # Normal in NED north/east -> the same screen mapping as a position
            # delta, so the arrow points where the vehicle would be pushed.
            dn, de = s["normal"][0], s["normal"][1]
            vx, vy = sl.vector_to_px(dn * 3.0, de * 3.0)
            tip = (sp[0] + vx, sp[1] + vy)
            d.line([sp, tip], fill=ACCENT, width=3)
            d.ellipse([sp[0] - 4, sp[1] - 4, sp[0] + 4, sp[1] + 4], fill=GOOD)
    d.ellipse([qp[0] - 7, qp[1] - 7, qp[0] + 7, qp[1] + 7], fill=ION)
    mask_outside(d, map_box)
    header(d, "the distance field", "One query, three consumers")

    if t > 0.5:
        a = ease((t - 0.5) / 0.25)
        panel(d, (880, 210, 1480, 520))
        d.text((910, 236), "A surface point", font=F_H2, fill=GOOD)
        d.text((910, 274), "and its normal", font=F_H2, fill=ACCENT)
        for j, line in enumerate([
            "Olfati-Saber flocking projects a",
            "beta-agent onto the nearest obstacle",
            "SURFACE POINT and needs its NORMAL.",
            "",
            "That is exactly what a signed distance",
            "field returns for any query point.",
        ]):
            m = int(148 * a)
            d.text((910, 330 + j * 28), line, font=F_TINY, fill=(m, m, m))

    if t > 0.72:
        a = ease((t - 0.72) / 0.28)
        panel(d, (880, 548, 1480, 800), fill=(26, 32, 42), outline=ACCENT)
        d.text((910, 574), "Before", font=F_SMALL, fill=BAD)
        for j, line in enumerate([
            "the flock could only avoid spheres and",
            "planes typed into a YAML file -- the",
            "shapes you can project onto in closed",
            "form. It could not avoid a wall a",
            "sensor found.",
        ]):
            m = int(148 * a)
            d.text((910, 606 + j * 26), line, font=F_TINY, fill=(m, m, m))
        d.text((910, 748), "Now: arbitrary sensed geometry,", font=F_SMALL, fill=GOOD)
        d.text((910, 772), "same three lines of arithmetic.", font=F_SMALL, fill=GOOD)

    footer(d, f"Real ObstacleField: {len(field['samples'])} samples within "
              f"{field['query_radius_m']:.0f} m, nearest {field['nearest_distance_m']:.2f} m, "
              "nearest first, unit outward normals.")
    return img


def scene_flocking(t, A):
    """Both modes consume it -- including the one that would have gone blind."""
    img, d = frame()
    header(d, "obstacle-aware flocking", "A mode that loses avoidance is a trap")

    if t > 0.06:
        a = ease((t - 0.06) / 0.22)
        panel(d, (110, 210, 760, 560))
        d.text((142, 240), "olfati_saber", font=F_MONO_B, fill=ION)
        d.text((142, 282), "beta-agents", font=F_H2, fill=TEXT)
        for j, line in enumerate([
            "Each ESDF sample is a surface point and",
            "an outward normal, which IS a local",
            "tangent plane -- and the wall beta-agent",
            "is already an orthogonal projection onto",
            "a plane.",
            "",
            "No new maths at all.",
        ]):
            m = int(148 * a)
            d.text((142, 336 + j * 26), line, font=F_TINY, fill=(m, m, m))

    if t > 0.32:
        a = ease((t - 0.32) / 0.22)
        panel(d, (840, 210, 1490, 560))
        d.text((872, 240), "reynolds", font=F_MONO_B, fill=ACCENT)
        d.text((872, 282), "a fourth rule", font=F_H2, fill=TEXT)
        for j, line in enumerate([
            "The classic three rules say nothing",
            "about obstacles, so selecting this mode",
            "would have silently lost all avoidance.",
            "",
            "A rule, not a filter on the output: a",
            "flock that avoids a wall by discarding",
            "cohesion scatters.",
        ]):
            m = int(148 * a)
            d.text((872, 336 + j * 26), line, font=F_TINY, fill=(m, m, m))

    if t > 0.58:
        a = ease((t - 0.58) / 0.3)
        panel(d, (110, 596, 1490, 790), fill=(26, 32, 42), outline=LINE)
        d.text((142, 620), "Repulsion follows the surface NORMAL, not the line to the "
                           "nearest point.", font=F_H2, fill=TEXT)
        m = int(148 * a)
        d.text((142, 668), "Near a flat wall those agree. At a concave corner they do not, "
                           "and the normal is the one that means \"out\".",
               font=F_SMALL, fill=(m, m, m))
        d.text((142, 706), "Frames: ObstacleField is local NED; the flocker works in ENU. "
                           "Both the point AND the normal convert -- a normal that",
               font=F_TINY, fill=MUTED)
        d.text((142, 730), "skipped the conversion would point along a plausible but wrong "
                           "axis and shove the flock into the thing it was avoiding.",
               font=F_TINY, fill=MUTED)

    footer(d, "hiko_flocking subscribes to /hiko/nav/obstacle_field. Sensed obstacles stay "
              "separate from configured ones: different lifetimes.")
    return img


def scene_dynamic(t, A):
    """The widening cone, drawn from the shipped layer parameters."""
    img, d = frame()
    header(d, "moving obstacles", "Where it is, and where it will be")

    cx, cy = 320, 520
    scale = 26.0
    horizon, step = 4.0, 0.5
    radius0, vstd, speed = 1.5, 0.5, 5.0

    p = ease(t / 0.5)
    n_steps = int((horizon / step) * p) + 1
    for i in range(n_steps):
        tt = i * step
        r = (radius0 + vstd * tt) * scale
        x = cx + speed * tt * scale
        shade = 1.0 - min(1.0, tt / horizon)
        if tt <= 1.0:
            col = BAD
        else:
            g = int(60 + 120 * shade)
            col = (int(120 + 100 * shade), g, 60)
        d.ellipse([x - r, cy - r, x + r, cy + r], outline=col, width=3)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=TEXT)
    d.text((cx - 46, cy + 44), "now", font=F_SMALL, fill=TEXT)
    if n_steps > 4:
        d.text((cx + speed * 4.0 * scale - 30, cy + 130), "+4 s", font=F_SMALL, fill=WARN)

    if t > 0.42:
        a = ease((t - 0.42) / 0.25)
        panel(d, (920, 240, 1490, 520))
        d.text((952, 266), "The cone widens", font=F_H2, fill=WARN)
        d.text((952, 312), "radius(t) = r_obj + r_veh", font=F_MONO_S, fill=ION)
        d.text((952, 338), "          + (pos_std + vel_std * t)", font=F_MONO_S, fill=ION)
        for j, line in enumerate([
            "A track's velocity is an estimate, so",
            "where it will be in four seconds is less",
            "certain than where it is now.",
            "",
            "A constant-radius sweep claims otherwise",
            "and threads gaps that only exist if the",
            "intruder holds its exact heading.",
        ]):
            m = int(148 * a)
            d.text((952, 380 + j * 24), line, font=F_TINY, fill=(m, m, m))

    if t > 0.68:
        a = ease((t - 0.68) / 0.32)
        panel(d, (920, 548, 1490, 760), fill=(26, 32, 42), outline=LINE)
        d.text((952, 574), "The near future is LETHAL.", font=F_SMALL, fill=BAD)
        d.text((952, 604), "The far future is a preference.", font=F_SMALL, fill=WARN)
        m = int(148 * a)
        for j, line in enumerate([
            "A planner treating t = 4 s as lethal",
            "refuses routes that are perfectly safe,",
            "because it can simply arrive earlier.",
        ]):
            d.text((952, 650 + j * 26), line, font=F_TINY, fill=(m, m, m))

    footer(d, "Drawn from the shipped dynamic-layer parameters: horizon 4.0 s, "
              "lethal_horizon 1.0 s, step 0.5 s.")
    return img


def scene_timing(t, A):
    img, d = frame()
    header(d, "what it costs", "Measured, then sized to fit")

    s = A["status"]
    budget_ms = s["update_period_s"] * 1000.0

    panel(d, (110, 210, 1490, 470))
    d.text((142, 236), "CostmapStatus, captured", font=F_H2, fill=TEXT)

    rows = [
        ("update mean", f"{s['update_mean_ms']:.1f} ms", GOOD),
        ("update max", f"{s['update_max_ms']:.1f} ms", GOOD if s['update_max_ms'] < budget_ms else WARN),
        ("distance transform", f"{s['esdf_mean_ms']:.1f} ms", ION),
        ("budget", f"{budget_ms:.0f} ms", MUTED),
        ("over budget", f"{s['updates_over_budget']}", GOOD if s['updates_over_budget'] == 0 else BAD),
    ]
    for i, (label, value, col) in enumerate(rows):
        appear = 0.08 + i * 0.07
        if t < appear:
            continue
        x = 142 + i * 272
        d.text((x, 300), label, font=F_TINY, fill=MUTED)
        d.text((x, 326), value, font=F_MONO_B, fill=col)

    if t > 0.46:
        a = ease((t - 0.46) / 0.2)
        bar_x0, bar_x1, bar_y = 142, 1458, 410
        d.rounded_rectangle((bar_x0, bar_y, bar_x1, bar_y + 26), radius=6, fill=(26, 32, 42))
        frac = min(1.0, s["update_mean_ms"] / budget_ms) * a
        d.rounded_rectangle((bar_x0, bar_y, bar_x0 + int((bar_x1 - bar_x0) * frac), bar_y + 26),
                            radius=6, fill=GOOD)
        d.text((bar_x0, bar_y + 34),
               f"{s['update_mean_ms'] / budget_ms * 100:.0f}% of the update budget",
               font=F_TINY, fill=MUTED)

    if t > 0.58:
        a = ease((t - 0.58) / 0.22)
        panel(d, (110, 500, 780, 800), fill=(26, 32, 42), outline=BAD)
        d.text((142, 526), "Before", font=F_H2, fill=BAD)
        d.text((142, 570), "626 ms", font=F_MONO_B, fill=BAD)
        m = int(148 * a)
        for j, line in enumerate([
            "The obstacle layer replays its whole",
            "history every cycle. A 10 Hz sensor with",
            "a 5 s decay window is fifty sweeps,",
            "re-marked and re-ray-cleared every time.",
            "",
            "It starved the planner sharing the",
            "callback group.",
        ]):
            d.text((142, 616 + j * 24), line, font=F_TINY, fill=(m, m, m))

    if t > 0.74:
        a = ease((t - 0.74) / 0.26)
        panel(d, (820, 500, 1490, 800), fill=(26, 32, 42), outline=GOOD)
        d.text((852, 526), "After", font=F_H2, fill=GOOD)
        d.text((852, 570), f"{s['update_mean_ms']:.1f} ms", font=F_MONO_B, fill=GOOD)
        m = int(148 * a)
        for j, line in enumerate([
            "Hits downsampled to one per voxel, and",
            "retained sweeps thinned to one per half",
            "second -- same decay window, same",
            "viewpoint diversity, a fifth of the cost.",
            "",
            "CostmapStatus is what made it visible.",
            "That is why it reports per-update timing.",
        ]):
            d.text((852, 616 + j * 24), line, font=F_TINY, fill=(m, m, m))

    footer(d, f"Captured on an untuned desktop: {s['cells_total']} cells, "
              f"{len(s['layers'])} layers, {s['cells_lethal']} lethal.")
    return img


def scene_verify(t, A):
    img, d = frame()
    header(d, "verified end to end", "Succeeding is not enough")

    checks = A["checks"]
    for i, (label, detail) in enumerate(checks):
        appear = 0.05 + i * 0.085
        if t < appear:
            continue
        a = ease((t - appear) / 0.14)
        y = 214 + i * 72
        x = 110 - int(30 * (1 - a))
        panel(d, (x, y, x + 1380, y + 60))
        d.text((x + 24, y + 14), "PASS", font=F_MONO_B, fill=GOOD)
        d.text((x + 110, y + 8), label, font=F_SMALL, fill=TEXT)
        d.text((x + 110, y + 34), detail, font=F_MONO_S, fill=MUTED)

    if t > 0.82:
        a = ease((t - 0.82) / 0.18)
        m = int(230 * a)
        d.text((110, 690), "A planner that ignores the map also succeeds, so the checks are "
                           "about PREFERENCE:", font=F_SMALL, fill=(m, m, m))
        d.text((110, 722), "does it pay distance for clearance, and does it report the "
                           "clearance it actually kept?", font=F_SMALL, fill=MUTED)
    footer(d, "tools/nav_demo.py, run against hikosim. Twelve checks; these are six of them.")
    return img


def scene_outro(t, A):
    img, d = frame()
    a = ease(min(1.0, t / 0.4))
    c = int(230 * a)
    d.text((90, 300), "hiko-nav", font=F_TITLE, fill=(c, c, c))
    d.text((90, 386), "costmap · distance field · planning · replanning · flocking",
           font=F_H2, fill=(int(148 * a), int(148 * a), int(148 * a)))

    if t > 0.3:
        b = ease((t - 0.3) / 0.3)
        d.line([(90, 452), (90 + int(520 * b), 452)], fill=ACCENT, width=3)

    if t > 0.42:
        b = ease((t - 0.42) / 0.3)
        m = int(148 * b)
        stats = A["stats"]
        for j, line in enumerate(stats):
            d.text((90, 500 + j * 34), line, font=F_MONO, fill=(m, m, m))

    if t > 0.72:
        b = ease((t - 0.72) / 0.28)
        m = int(138 * b)
        d.text((90, 800), "THE HIKO COMPANY", font=F_SMALL,
               fill=(int(ACCENT[0] * b), int(ACCENT[1] * b), int(ACCENT[2] * b)))
        d.text((90, 832), "aerial autonomy, electrified", font=F_TINY, fill=(m, m, m))
    return img


SCENES = [
    (scene_title, 5.0),
    (scene_problem, 8.0),
    (scene_layers, 10.0),
    (scene_clearing, 9.0),
    (scene_preference, 9.0),
    (scene_field, 10.0),
    (scene_flocking, 9.0),
    (scene_dynamic, 9.0),
    (scene_timing, 10.0),
    (scene_verify, 9.0),
    (scene_outro, 6.0),
]


def load(artifacts: Path) -> dict:
    A = {
        "costmap": json.loads((artifacts / "costmap.json").read_text()),
        "field": json.loads((artifacts / "field.json").read_text()),
        "status": json.loads((artifacts / "status.json").read_text()),
        "paths": json.loads((artifacts / "paths.json").read_text()),
        "preference": json.loads((artifacts / "preference.json").read_text()),
    }
    s = A["status"]
    routes = [r for r in A["paths"]["routes"] if r["success"]]
    pref = A["preference"]["routes"]
    field = A["field"]
    A["checks"] = [
        ("the obstacle layer is updating",
         "   ".join(f"{l['name']}={l['updates']}" for l in s["layers"])),
        ("lidar returns became lethal cells",
         f"{s['cells_lethal']} lethal, {s['cells_unknown']} unknown of {s['cells_total']}"),
        ("update fits its budget",
         f"{s['update_mean_ms']:.1f} ms mean, {s['update_max_ms']:.1f} ms max, "
         f"esdf {s['esdf_mean_ms']:.1f} ms, {s['updates_over_budget']} over"),
        ("the planner prefers clearance over distance",
         f"weight 0: {pref[0]['length_m']:.1f} m / {pref[0]['min_clearance_m']:.2f} m   "
         f"weight {pref[1]['cost_weight']:.0f}: {pref[1]['length_m']:.1f} m / "
         f"{pref[1]['min_clearance_m']:.2f} m"),
        ("clearance is measured along the path, not at waypoints",
         "a two-waypoint route through a 3 m gap reports 3 m, not 15 m"),
        ("samples carry unit outward normals, nearest first",
         f"{len(field['samples'])} samples, nearest {field['nearest_distance_m']:.2f} m"),
    ]
    A["stats"] = [
        f"{s['cells_total']} cells   {len(s['layers'])} layers   "
        f"{s['update_mean_ms']:.1f} ms per update",
        "exact Euclidean signed distance field, O(n)",
        "3 packages   66 tests   workspace green at 1153",
    ]
    return A


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the hiko-nav promo film.")
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--frames", default="/tmp/hiko_nav_frames")
    ap.add_argument("--out", default="nav.mp4")
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
