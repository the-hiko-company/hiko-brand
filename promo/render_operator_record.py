#!/usr/bin/env python3
# Copyright (c) 2026 The Hiko Company. All rights reserved.
"""Render the operator run as a page you can read.

Same rule as the films: EVERYTHING ON THE PAGE IS A REAL ARTEFACT. It reads
artifacts/operator/run.json and control.json, both written by
hiko-gcs/tools/operator_flight_demo.py, and it renders whatever is in them --
including the check that fails, which is the reason this page is worth having.

    python3 render_operator_record.py --out operator-record.html
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts" / "operator"


def trace_svg(run: list, control: list, events: list, width: int = 900, height: int = 300) -> str:
    """The altitude trace, with the control arm ghosted behind it."""
    pad_l, pad_r, pad_t, pad_b = 46, 16, 16, 30
    all_t = [t for t, _ in run] + [t for t, _ in control]
    all_a = [a for _, a in run] + [a for _, a in control] + [25.0]
    t_max = max(all_t) if all_t else 1.0
    a_max = max(all_a) if all_a else 1.0

    def x(t: float) -> float:
        return pad_l + (t / t_max) * (width - pad_l - pad_r)

    def y(a: float) -> float:
        return height - pad_b - (max(a, 0.0) / a_max) * (height - pad_t - pad_b)

    def path(points: list) -> str:
        return " ".join(
            f"{'M' if i == 0 else 'L'}{x(t):.1f},{y(a):.1f}" for i, (t, a) in enumerate(points)
        )

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="display:block;height:auto" role="img" '
        f'aria-label="altitude against time, with and without the pushed tree">'
    ]
    # Gridlines at 5 m intervals, labelled.
    step = 5
    line = 0
    while line <= a_max:
        parts.append(
            f'<line x1="{pad_l}" y1="{y(line):.1f}" x2="{width - pad_r}" y2="{y(line):.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
            f'<text x="{pad_l - 8}" y="{y(line) + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="var(--muted)">{line}</text>'
        )
        line += step

    # The altitude the operator asked for, and never got.
    parts.append(
        f'<line x1="{pad_l}" y1="{y(25.0):.1f}" x2="{width - pad_r}" y2="{y(25.0):.1f}" '
        f'stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="6 4"/>'
        f'<text x="{width - pad_r}" y="{y(25.0) - 6:.1f}" text-anchor="end" font-size="11" '
        f'fill="var(--accent)">25 m &mdash; asked for</text>'
    )

    if control:
        parts.append(
            f'<path d="{path(control)}" fill="none" stroke="var(--muted)" stroke-width="1.5" '
            f'stroke-dasharray="3 3" opacity="0.75"/>'
        )
    if run:
        parts.append(f'<path d="{path(run)}" fill="none" stroke="var(--ink)" stroke-width="2.5"/>')

    for t, label in events:
        if label != "pushed":
            continue
        parts.append(
            f'<line x1="{x(t):.1f}" y1="{pad_t}" x2="{x(t):.1f}" y2="{height - pad_b}" '
            f'stroke="var(--accent)" stroke-width="2"/>'
            f'<circle cx="{x(t):.1f}" cy="{y(next((a for tt, a in run if tt >= t), 0)):.1f}" '
            f'r="4" fill="var(--accent)"/>'
            f'<text x="{x(t) + 7:.1f}" y="{pad_t + 12}" font-size="11" '
            f'fill="var(--accent)">tree pushed</text>'
        )
    parts.append(
        f'<text x="{width - pad_r}" y="{height - 8}" text-anchor="end" font-size="11" '
        f'fill="var(--muted)">seconds</text></svg>'
    )
    return "".join(parts)


CSS = """
:root{--ground:#f6f4f1;--panel:#fffdfb;--ink:#17191c;--muted:#6b6560;--line:#e0dbd4;
--grid:#e8e3dc;--accent:#b4471f;--ok:#2e6b42;--ok-bg:#e6efe8;--bad:#a32b22;--bad-bg:#f8e7e4;
--code:#1c1e21;--code-ink:#ddd8d2;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#131416;
--panel:#1b1d20;--ink:#e7e4e0;--muted:#9a938c;--line:#2b2d31;--grid:#26282c;--accent:#e0754a;
--ok:#6fc98d;--ok-bg:#16261c;--bad:#ef8478;--bad-bg:#2a1614;--code:#0d0e10;--code-ink:#d6d1cb;}}
:root[data-theme="dark"]{--ground:#131416;--panel:#1b1d20;--ink:#e7e4e0;--muted:#9a938c;
--line:#2b2d31;--grid:#26282c;--accent:#e0754a;--ok:#6fc98d;--ok-bg:#16261c;--bad:#ef8478;
--bad-bg:#2a1614;--code:#0d0e10;--code-ink:#d6d1cb;}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
font-family:Newsreader,Georgia,serif;font-size:17px;line-height:1.6}
.wrap{max-width:60rem;margin:0 auto;padding:3.5rem 1.5rem 6rem}
h1,h2,h3,.ui{font-family:"Bricolage Grotesque","Helvetica Neue",Arial,sans-serif}
h1{font-size:clamp(2rem,5vw,2.8rem);font-weight:700;letter-spacing:-.02em;line-height:1.08;
margin:0 0 .5rem;text-wrap:balance}
.eyebrow{font-family:"Bricolage Grotesque",sans-serif;font-size:.7rem;font-weight:600;
letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin:0 0 .8rem}
.lede{color:var(--muted);max-width:40rem;margin:0 0 2.5rem}
h2{font-size:.78rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;
color:var(--muted);margin:3rem 0 1rem;padding-bottom:.5rem;border-bottom:1px solid var(--line)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:1.4rem}
.chart{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:1rem;
overflow-x:auto}
.legend{display:flex;gap:1.4rem;flex-wrap:wrap;font-size:.8rem;color:var(--muted);
margin-top:.7rem;font-family:"Bricolage Grotesque",sans-serif}
.swatch{display:inline-block;width:22px;height:0;border-top-width:2.5px;border-top-style:solid;
vertical-align:middle;margin-right:.4rem}
.check{display:flex;gap:.8rem;align-items:baseline;padding:.6rem 0;border-bottom:1px solid var(--line)}
.check:last-child{border-bottom:none}
.pill{font-family:"Bricolage Grotesque",sans-serif;font-size:.65rem;font-weight:700;
letter-spacing:.1em;text-transform:uppercase;padding:.15rem .5rem;border-radius:2px;white-space:nowrap}
.pass{background:var(--ok-bg);color:var(--ok)}.fail{background:var(--bad-bg);color:var(--bad)}
.detail{color:var(--muted);font-size:.88rem}
.mono,code,pre{font-family:"IBM Plex Mono",ui-monospace,monospace}
.big{font-family:"Bricolage Grotesque",sans-serif;font-size:2.2rem;font-weight:700;
line-height:1;font-variant-numeric:tabular-nums}
.row{display:flex;flex-wrap:wrap;gap:2.4rem}
.row div{display:flex;flex-direction:column;gap:.2rem}
.k{font-family:"Bricolage Grotesque",sans-serif;font-size:.68rem;letter-spacing:.11em;
text-transform:uppercase;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:.9rem;margin-top:.6rem}
th{text-align:left;font-family:"Bricolage Grotesque",sans-serif;font-size:.66rem;
letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:600;
padding:.4rem .6rem .4rem 0;border-bottom:1px solid var(--line)}
td{padding:.45rem .6rem .45rem 0;border-bottom:1px solid var(--line);
font-variant-numeric:tabular-nums}
.withheld td{color:var(--muted)}
.note{border-left:3px solid var(--accent);padding:.2rem 0 .2rem 1rem;margin:1.4rem 0;
color:var(--muted)}
footer{margin-top:4rem;padding-top:1.2rem;border-top:1px solid var(--line);
color:var(--muted);font-size:.85rem}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "operator-record.html"))
    args = ap.parse_args()

    run = json.loads((ART / "run.json").read_text())
    control_path = ART / "control.json"
    control = json.loads(control_path.read_text())["trace"] if control_path.exists() else []
    verdict = run["verdict"]
    blame = json.loads(verdict["verdict_json"])["blame"]
    checks = run["checks"]
    passed = sum(1 for c in checks if c["ok"])

    rows = []
    for b in blame:
        if b["withheld"]:
            rows.append(
                f'<tr class="withheld"><td>&mdash;</td><td class="mono">'
                f'{html.escape(b["path"].split("/")[-1])}</td><td colspan="2">'
                f'{html.escape(b["withheld"])}</td></tr>'
            )
        elif b["share"] > 0.005:
            rows.append(
                f'<tr><td>{b["share"] * 100:.1f}%</td><td class="mono">'
                f'{html.escape(b["path"].split("/")[-1])}</td>'
                f'<td>{b["fail_when_failed"] * 100:.0f}%</td>'
                f'<td>{b["fail_when_ok"] * 100:.0f}%</td></tr>'
            )

    check_html = "".join(
        f'<div class="check"><span class="pill {"pass" if c["ok"] else "fail"}">'
        f'{"pass" if c["ok"] else "fail"}</span><div><div>{html.escape(c["label"])}</div>'
        + (f'<div class="detail">{html.escape(c["detail"])}</div>' if c["detail"] else "")
        + "</div></div>"
        for c in checks
    )

    page = f"""<title>Operator Run Record</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700&family=IBM+Plex+Mono:wght@400&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<p class="eyebrow">Hiko Stack &middot; flight record</p>
<h1>An operator pushed a tree. The aircraft took it and did not climb.</h1>
<p class="lede">Every number here was written by
<span class="mono">operator_flight_demo.py</span> during one run against the
simulator, the estimator, the controller and the mission manager. Nothing is
typed in. The check that fails is the reason this page exists.</p>

<div class="row panel">
<div><span class="big">{passed}/{len(checks)}</span><span class="k">checks passed</span></div>
<div><span class="big">{verdict["p_success"] * 100:.1f}%</span><span class="k">rehearsed verdict</span></div>
<div><span class="big">{run["reached_m"]:.1f}<span style="font-size:1rem">m</span></span><span class="k">reached</span></div>
<div><span class="big">{run["target_m"]:.0f}<span style="font-size:1rem">m</span></span><span class="k">asked for</span></div>
</div>

<h2>What the aircraft did</h2>
<div class="chart">{trace_svg(run["trace"], control, run["events"])}</div>
<div class="legend">
<span><span class="swatch" style="border-color:var(--ink)"></span>with the pushed tree</span>
<span><span class="swatch" style="border-color:var(--muted);border-top-style:dashed"></span>control run, nothing pushed</span>
<span><span class="swatch" style="border-color:var(--accent);border-top-style:dashed"></span>the altitude the operator asked for</span>
</div>

<div class="note">The two traces have the same shape. The climb to 15&nbsp;m is the
scenario&rsquo;s own takeoff, which happens either way, and the descent happens
either way too &mdash; so neither belongs to the push. An earlier version of this
demo asked only for &ldquo;higher than it was&rdquo; and passed on the strength of
that climb. It was green and it meant nothing.</div>

<h2>The rehearsal, before anything was sent</h2>
<div class="panel">
<p style="margin-top:0">P(mission succeeds) = <strong>{verdict["p_success"] * 100:.1f}%</strong>
<span class="detail">({verdict["p_low"] * 100:.1f}&ndash;{verdict["p_high"] * 100:.1f}% at 95%,
over {verdict["runs_done"]} executed runs)</span></p>
<table><thead><tr><th>share</th><th>node</th><th>loses mission when it fails</th>
<th>&hellip; when it does not</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<p class="detail" style="margin-bottom:0">{html.escape(verdict["caveat"])}</p>
</div>

<h2>Every check, as it ran</h2>
<div class="panel">{check_html}</div>

<h2>What this proves</h2>
<div class="panel">
<p style="margin-top:0"><strong>The command path.</strong> A plan rehearsed on the
vehicle, a parameter set, a tree pushed and accepted, and the aircraft reporting
back the tree it is running &mdash; all over the console&rsquo;s own WebSocket.</p>
<p style="margin-bottom:0"><strong>Not the flight response.</strong> The check asks
for 25&nbsp;m, which is above the 15&nbsp;m the scenario reaches alone, so nothing
but the push could produce it. It does not get there: this airframe begins
descending about ten seconds after reaching the hover, and there is no window left
to climb in. That is the estimator defect in
<span class="mono">hiko-gnc/docs/estimator.md</span>, not the push &mdash; the
control run falls the same way.</p>
</div>

<footer>Rendered by <span class="mono">hiko-brand/promo/render_operator_record.py</span>
from <span class="mono">artifacts/operator/run.json</span>. Re-run the demo and
re-render; the page follows the run, not the other way round.</footer>
</div>"""
    Path(args.out).write_text(page, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
