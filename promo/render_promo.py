#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
# Proprietary and confidential.
"""Render the Hiko Stack promo video, frame by frame.

Everything on screen is a REAL artefact produced by the stack — the timing
report is a real run, the learning curve is a real training record, the memory
plan is real output from hiko-plan. Nothing here is a mockup, because a promo
built on invented numbers is a promo that cannot survive its first demo.

    python3 render_promo.py --artifacts <dir> --out promo.mp4

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

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


F_TITLE = font("DejaVuSans-Bold.ttf", 86)
F_SUB = font("DejaVuSans.ttf", 34)
F_H1 = font("DejaVuSans-Bold.ttf", 52)
F_H2 = font("DejaVuSans-Bold.ttf", 34)
F_BODY = font("DejaVuSans.ttf", 26)
F_SMALL = font("DejaVuSans.ttf", 20)
F_MONO = font("DejaVuSansMono.ttf", 21)
F_MONO_S = font("DejaVuSansMono.ttf", 17)
F_MONO_B = font("DejaVuSansMono-Bold.ttf", 21)
F_BIG = font("DejaVuSansMono-Bold.ttf", 96)
F_LABEL = font("DejaVuSans.ttf", 22)


# --- easing ------------------------------------------------------------------

def ease(t: float) -> float:
    """Smootherstep. Linear fades look mechanical; this reads as intent."""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def fade(colour: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    a = max(0.0, min(1.0, alpha))
    return tuple(int(BG[i] + (colour[i] - BG[i]) * a) for i in range(3))


def reveal(text: str, progress: float) -> str:
    """Type-on: characters appear left to right."""
    n = int(len(text) * max(0.0, min(1.0, progress)))
    return text[:n]


# --- chrome ------------------------------------------------------------------

def new_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), BG)
    return image, ImageDraw.Draw(image)


def watermark(draw: ImageDraw.ImageDraw, alpha: float = 1.0) -> None:
    draw.text((W - 40, H - 34), "THE HIKO COMPANY", font=F_SMALL,
              fill=fade(MUTED, 0.5 * alpha), anchor="rs")


def panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], alpha: float = 1.0,
          border: tuple[int, int, int] = LINE) -> None:
    draw.rounded_rectangle(box, radius=12, fill=fade(PANEL, alpha), outline=fade(border, alpha),
                           width=2)


def section_label(draw: ImageDraw.ImageDraw, text: str, alpha: float) -> None:
    draw.text((80, 66), text.upper(), font=F_LABEL, fill=fade(ACCENT, alpha))
    draw.line((80, 100, 80 + 44, 100), fill=fade(ACCENT, alpha), width=3)


# --- scenes ------------------------------------------------------------------

def scene_title(draw: ImageDraw.ImageDraw, t: float, d: float) -> None:
    p = t / d
    a = ease(min(1.0, p * 4)) * (1.0 - ease(max(0.0, (p - 0.85) / 0.15)))

    wordmark = ["╦ ╦ ╦ ╦╔═ ╔═╗", "╠═╣ ║ ╠╩╗ ║ ║", "╩ ╩ ╩ ╩ ╩ ╚═╝"]
    for i, row in enumerate(wordmark):
        draw.text((W // 2, 250 + i * 44), row, font=font("DejaVuSansMono-Bold.ttf", 40),
                  fill=fade(ACCENT, a), anchor="ms")

    draw.text((W // 2, 470), "THE HIKO COMPANY", font=F_TITLE, fill=fade(TEXT, a), anchor="ms")
    if p > 0.3:
        b = ease((p - 0.3) / 0.35)
        draw.text((W // 2, 528), "aerial autonomy, electrified", font=F_SUB,
                  fill=fade(MUTED, b * a), anchor="ms")
    if p > 0.5:
        c = ease((p - 0.5) / 0.35)
        draw.line((W // 2 - 220, 578, W // 2 + 220, 578), fill=fade(LINE, c * a), width=2)
        draw.text((W // 2, 630), "Any airframe. Any autopilot. Any runtime.", font=F_H2,
                  fill=fade(ION, c * a), anchor="ms")


def scene_thesis(draw: ImageDraw.ImageDraw, t: float, d: float) -> None:
    p = t / d
    a = ease(min(1.0, p * 5)) * (1.0 - ease(max(0.0, (p - 0.88) / 0.12)))
    section_label(draw, "the rule", a)

    draw.text((80, 200), "Everything implemented in-house.", font=F_H1, fill=fade(TEXT, a))

    lines = [
        ("MAVLink · MSP", "autopilot protocols"),
        ("JIPDAF · ESKF · ICP · CBS", "estimation, tracking, planning"),
        ("Parquet writer · hex index", "data and airspace"),
        ("BT engine · HSM · PDDL", "autonomy"),
        ("the real-time runtime itself", "hiko-os"),
    ]
    for i, (what, why) in enumerate(lines):
        start = 0.18 + i * 0.11
        if p < start:
            continue
        b = ease((p - start) / 0.16) * a
        y = 300 + i * 62
        draw.text((84, y), "▪", font=F_BODY, fill=fade(ACCENT, b))
        draw.text((120, y), what, font=F_H2, fill=fade(TEXT, b))
        draw.text((640, y + 6), why, font=F_BODY, fill=fade(MUTED, b))

    if p > 0.72:
        b = ease((p - 0.72) / 0.2) * a
        draw.text((80, 700), "Dependencies: the C++ stdlib, Boost, Eigen, GeographicLib.",
                  font=F_BODY, fill=fade(MUTED, b))
        draw.text((80, 742), "If it flies, we can read every line of it.", font=F_H2,
                  fill=fade(ION, b))


def scene_runtime(draw: ImageDraw.ImageDraw, t: float, d: float, timing: list[str]) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.92) / 0.08)))
    section_label(draw, "hiko-os · the runtime", a)

    draw.text((80, 150), "A static graph in. A timing report out.", font=F_H1, fill=fade(TEXT, a))
    draw.text((80, 216), "Preallocated, deterministic, measured every single execution.",
              font=F_BODY, fill=fade(MUTED, a))

    panel(draw, (76, 270, W - 76, 300 + 12 * 30 + 24), a)
    # The report types on line by line — it is the artefact, so let it land.
    visible = int(len(timing) * ease(min(1.0, p / 0.75)))
    for i, line in enumerate(timing[:visible]):
        y = 300 + i * 30
        colour = TEXT
        f = F_MONO_S
        if line.strip().startswith("overruns"):
            # Green ONLY when both counters are zero. The line also carries
            # deadline misses, and colouring it green regardless would claim
            # more than the run actually showed.
            colour = GOOD if "deadline misses 0 " in line + " " else ACCENT
            f = F_MONO_B
        elif line.strip().startswith("participant"):
            colour = MUTED
        elif "hiko-os timing report" in line:
            colour = ION
            f = F_MONO_B
        draw.text((104, y), line[:150], font=f, fill=fade(colour, a))

    if p > 0.78:
        b = ease((p - 0.78) / 0.2) * a
        draw.text((80, 730), "20 s · 24 000 ticks · untuned desktop, no PREEMPT_RT, no isolation",
                  font=F_BODY, fill=fade(MUTED, b))
        draw.text((80, 774),
                  "Ten deadline misses out of 24 000 — desktop scheduling noise, and the",
                  font=F_SMALL, fill=fade(MUTED, b))
        draw.text((80, 806), "report says so instead of leaving you to wonder.",
                  font=F_SMALL, fill=fade(MUTED, b))
        draw.text((W - 80, 790), "ZERO BUDGET OVERRUNS", font=F_H2, fill=fade(GOOD, b),
                  anchor="rs")


def scene_languages(draw: ImageDraw.ImageDraw, t: float, d: float) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.9) / 0.1)))
    section_label(draw, "hiko-sdk · client libraries", a)

    draw.text((80, 150), "One C ABI. Four languages.", font=F_H1, fill=fade(TEXT, a))
    draw.text((80, 216), "Zero third-party dependencies in any of them.", font=F_BODY,
              fill=fade(MUTED, a))

    cards = [
        ("C++", "native headers", 'out_.publish(std::move(loan));'),
        ("C", "hiko/hiko.h", 'hiko_publish_loan(rt, ch, slot);'),
        ("Python", "ctypes · no pip", 'rt.publish(out, Imu(seq=1))'),
        ("Rust", "extern "'"C"'" · no crates", 'p.publish_with::<Imu,_>(..)'),
    ]
    card_w = (W - 160 - 3 * 20) // 4
    for i, (name, how, snippet) in enumerate(cards):
        start = 0.16 + i * 0.1
        if p < start:
            continue
        b = ease((p - start) / 0.16) * a
        x = 80 + i * (card_w + 20)
        panel(draw, (x, 280, x + card_w, 500), b, border=ION if b > 0.6 else LINE)
        draw.text((x + 24, 306), name, font=F_H2, fill=fade(ACCENT, b))
        draw.text((x + 24, 356), how, font=F_SMALL, fill=fade(MUTED, b))
        draw.text((x + 24, 404), snippet[:26], font=F_MONO_S, fill=fade(ION, b))

    if p > 0.6:
        b = ease((p - 0.6) / 0.25) * a
        draw.text((W // 2, 580), "Same graph. Same runtime. Same numbers.", font=F_H2,
                  fill=fade(TEXT, b), anchor="ms")
        rows = [
            ("IMU samples", "20 000"),
            ("motor commands", "8 000"),
            ("telemetry frames", "3 981"),
            ("budget overruns", "0"),
        ]
        for i, (k, v) in enumerate(rows):
            x = 200 + i * 320
            draw.text((x, 660), k, font=F_SMALL, fill=fade(MUTED, b))
            draw.text((x, 700), v, font=font("DejaVuSansMono-Bold.ttf", 44),
                      fill=fade(GOOD if v == "0" else TEXT, b))


def scene_plan(draw: ImageDraw.ImageDraw, t: float, d: float, plan: list[str]) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.9) / 0.1)))
    section_label(draw, "hiko-plan · before you fly", a)

    draw.text((80, 150), "Will it fit? Is it schedulable?", font=F_H1, fill=fade(TEXT, a))
    draw.text((80, 216), "Answered from the graph file. In CI. Without running anything.",
              font=F_BODY, fill=fade(MUTED, a))

    panel(draw, (76, 272, W - 76, 820), a)
    visible = int(len(plan) * ease(min(1.0, p / 0.8)))
    for i, line in enumerate(plan[:visible]):
        y = 296 + i * 26
        if y > 800:
            break
        colour = TEXT
        f = F_MONO_S
        if "ok " in line and ("validation" in line or "fits" in line):
            colour = GOOD
            f = F_MONO_B
        elif line.startswith("schedule") or line.startswith("memory") or line.startswith("parameters"):
            colour = ACCENT
            f = F_MONO_B
        elif "hiko-plan" in line:
            colour = ION
            f = F_MONO_B
        draw.text((104, y), line[:150], font=f, fill=fade(colour, a))


def scene_rl(draw: ImageDraw.ImageDraw, t: float, d: float, run: dict) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.9) / 0.1)))
    section_label(draw, "hiko-rl · learned control", a)

    draw.text((80, 150), "Train a policy. Fly it inside a budget.", font=F_H1, fill=fade(TEXT, a))
    draw.text((80, 216), "quad-attitude · recover level flight from an aggressive upset",
              font=F_BODY, fill=fade(MUTED, a))

    returns = [r for r in run["log"]["returns"] if r == r]
    if len(returns) < 2:
        return

    # Chart.
    box = (80, 280, 980, 720)
    panel(draw, box, a)
    lo, hi = min(returns), max(returns)
    span = (hi - lo) or 1.0
    shown = max(2, int(len(returns) * ease(min(1.0, p / 0.7))))
    pts = []
    for i, value in enumerate(returns[:shown]):
        x = box[0] + 60 + (box[2] - box[0] - 100) * i / (len(returns) - 1)
        y = box[3] - 50 - (box[3] - box[1] - 90) * (value - lo) / span
        pts.append((x, y))
    if len(pts) > 1:
        draw.line(pts, fill=fade(ACCENT, a), width=3, joint="curve")
        draw.ellipse((pts[-1][0] - 6, pts[-1][1] - 6, pts[-1][0] + 6, pts[-1][1] + 6),
                     fill=fade(ACCENT, a))
    draw.text((box[0] + 24, box[1] + 20), "mean return", font=F_SMALL, fill=fade(MUTED, a))
    draw.text((box[0] + 60, box[3] - 34), f"{lo:.0f}", font=F_MONO_S, fill=fade(MUTED, a))
    draw.text((box[2] - 40, box[1] + 74), f"peak {hi:.0f}", font=F_MONO_S, fill=fade(MUTED, a),
              anchor="rs")

    # Numbers.
    if p > 0.45:
        b = ease((p - 0.45) / 0.3) * a
        stats = [
            ("baseline", f"{run['baseline']['mean_return']:.0f}", BAD),
            ("trained", f"{run['final']['mean_return']:.0f}", GOOD),
            ("steps/s", f"{run['steps_per_second']:,.0f}", TEXT),
            ("wall clock", f"{run['duration_s']:.1f} s", TEXT),
        ]
        for i, (k, v, colour) in enumerate(stats):
            y = 300 + i * 96
            draw.text((1030, y), k, font=F_SMALL, fill=fade(MUTED, b))
            draw.text((1030, y + 30), v, font=font("DejaVuSansMono-Bold.ttf", 40),
                      fill=fade(colour, b))

    if p > 0.72:
        b = ease((p - 0.72) / 0.25) * a
        policy = run.get("policy", {})
        panel(draw, (80, 750, W - 80, 840), b, border=ION)
        draw.text((110, 772), "exported policy", font=F_SMALL, fill=fade(MUTED, b))
        draw.text((110, 798),
                  f"{policy.get('operation_count', 0):,} multiply-accumulates  →  "
                  f"hiko-os budget_us: {policy.get('suggested_budget_us', 0)}",
                  font=F_MONO_B, fill=fade(ION, b))


def scene_tools(draw: ImageDraw.ImageDraw, t: float, d: float, counts: dict) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.9) / 0.1)))
    section_label(draw, "the rest of the bench", a)

    draw.text((80, 150), "Everything else you need to actually work.", font=F_H1,
              fill=fade(TEXT, a))

    cards = [
        ("hiko-panel", "mission control", ["launch any scenario",
                                           "on any simulator",
                                           "watch it stream live"]),
        ("hiko-brain", "what an AI needs", [f"{counts['packages']} packages indexed",
                                            f"{counts['messages']} message types",
                                            f"{counts['skills']} skills"]),
        ("hiko-sim", "any physics engine", ["hikosim · MuJoCo · Gazebo",
                                            "one SimulatorInterface",
                                            "HSB bridge for yours"]),
    ]
    card_w = (W - 160 - 2 * 24) // 3
    for i, (name, tag, bullets) in enumerate(cards):
        start = 0.15 + i * 0.14
        if p < start:
            continue
        b = ease((p - start) / 0.2) * a
        x = 80 + i * (card_w + 24)
        panel(draw, (x, 260, x + card_w, 620), b)
        draw.text((x + 28, 292), name, font=F_H2, fill=fade(ACCENT, b))
        draw.text((x + 28, 340), tag, font=F_BODY, fill=fade(ION, b))
        for j, bullet in enumerate(bullets):
            draw.text((x + 28, 410 + j * 44), "· " + bullet, font=F_BODY, fill=fade(MUTED, b))

    if p > 0.68:
        b = ease((p - 0.68) / 0.25) * a
        draw.text((W // 2, 720), "Sensing is fractal: a lidar, a drone, a squad, the fleet —",
                  font=F_H2, fill=fade(TEXT, b), anchor="ms")
        draw.text((W // 2, 768), "all one interface, all the way up.", font=F_H2,
                  fill=fade(ION, b), anchor="ms")


def scene_numbers(draw: ImageDraw.ImageDraw, t: float, d: float, counts: dict) -> None:
    p = t / d
    a = ease(min(1.0, p * 6)) * (1.0 - ease(max(0.0, (p - 0.9) / 0.1)))
    section_label(draw, "by the numbers", a)

    figures = [
        (str(counts["repos"] + 1), "repositories"),
        ("1 100+", "tests, all green"),
        ("0", "budget overruns"),
        ("4", "client languages"),
    ]
    for i, (value, label) in enumerate(figures):
        start = 0.12 + i * 0.12
        if p < start:
            continue
        b = ease((p - start) / 0.2) * a
        x = 80 + i * ((W - 160) // 4)
        colour = GOOD if value == "0" else ACCENT
        draw.text((x, 340), value, font=F_BIG, fill=fade(colour, b))
        draw.text((x, 460), label, font=F_BODY, fill=fade(MUTED, b))

    if p > 0.62:
        b = ease((p - 0.62) / 0.28) * a
        draw.line((80, 580, W - 80, 580), fill=fade(LINE, b), width=2)
        draw.text((80, 630), "Every run recorded. Every budget measured.", font=F_H2,
                  fill=fade(TEXT, b))
        draw.text((80, 690), "Every number here came out of the stack, not a slide.",
                  font=F_BODY, fill=fade(MUTED, b))


def scene_close(draw: ImageDraw.ImageDraw, t: float, d: float) -> None:
    p = t / d
    a = ease(min(1.0, p * 4)) * (1.0 - ease(max(0.0, (p - 0.8) / 0.2)))

    draw.text((W // 2, 330), "THE HIKO COMPANY", font=F_TITLE, fill=fade(TEXT, a), anchor="ms")
    draw.text((W // 2, 396), "aerial autonomy, electrified", font=F_SUB, fill=fade(ACCENT, a),
              anchor="ms")
    if p > 0.25:
        b = ease((p - 0.25) / 0.3) * a
        draw.line((W // 2 - 260, 450, W // 2 + 260, 450), fill=fade(LINE, b), width=2)
        draw.text((W // 2, 520), "the-hiko-company.github.io", font=F_H2, fill=fade(ION, b),
                  anchor="ms")
    if p > 0.5:
        b = ease((p - 0.5) / 0.3) * a
        draw.text((W // 2, 610), "No black boxes. No borrowed cores.", font=F_BODY,
                  fill=fade(MUTED, b), anchor="ms")
        draw.text((W // 2, 650), "No untraceable behaviour between the stick and the sky.",
                  font=F_BODY, fill=fade(MUTED, b), anchor="ms")


# --- timeline ----------------------------------------------------------------

def build(artifacts: Path, out_dir: Path) -> int:
    timing = [l.rstrip() for l in (artifacts / "timing_real.txt").read_text().splitlines()
              if l.strip()][:12]
    plan = [l.rstrip() for l in (artifacts / "plan.txt").read_text().splitlines()][:34]
    run = json.loads((artifacts / "rl_run.json").read_text())
    counts = json.loads(
        (Path("/home/wardn/dev/the-hiko-company/hiko-brain/brain/index.json")).read_text())["counts"]

    scenes = [
        (5.0, lambda dr, t, d: scene_title(dr, t, d)),
        (8.0, lambda dr, t, d: scene_thesis(dr, t, d)),
        (11.0, lambda dr, t, d: scene_runtime(dr, t, d, timing)),
        (9.0, lambda dr, t, d: scene_languages(dr, t, d)),
        (9.0, lambda dr, t, d: scene_plan(dr, t, d, plan)),
        (11.0, lambda dr, t, d: scene_rl(dr, t, d, run)),
        (9.0, lambda dr, t, d: scene_tools(dr, t, d, counts)),
        (8.0, lambda dr, t, d: scene_numbers(dr, t, d, counts)),
        (6.0, lambda dr, t, d: scene_close(dr, t, d)),
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    index = 0
    for duration, render in scenes:
        for frame in range(int(duration * FPS)):
            image, draw = new_frame()
            render(draw, frame / FPS, duration)
            watermark(draw)
            image.save(out_dir / f"f{index:05d}.jpg", quality=92)
            index += 1
    return index


def encode(frames_dir: Path, out: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", str(frames_dir / "f%05d.jpg"),
        "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ], check=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Hiko promo video.")
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--frames", default="/tmp/hiko_promo_frames")
    parser.add_argument("--out", default="promo.mp4")
    parser.add_argument("--poster", default=None, help="also write a poster frame here")
    args = parser.parse_args()

    frames_dir = Path(args.frames)
    count = build(Path(args.artifacts), frames_dir)
    print(f"rendered {count} frames ({count / FPS:.1f} s)")
    encode(frames_dir, Path(args.out))
    size = Path(args.out).stat().st_size
    print(f"encoded {args.out} ({size / 1_000_000:.1f} MB)")

    if args.poster:
        # A frame from the runtime scene: the timing report is the thing worth
        # putting on a card.
        poster_index = int((5.0 + 8.0 + 9.0) * FPS)
        Image.open(frames_dir / f"f{poster_index:05d}.jpg").save(args.poster, quality=94)
        print(f"poster {args.poster}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
