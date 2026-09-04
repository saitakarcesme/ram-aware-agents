#!/usr/bin/env python3
"""Render the minimal black-and-white benchmark social graphics."""

from __future__ import annotations

import html
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
WIDTH = 1600
HEIGHT = 900
FONT = "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"


def esc(value: object) -> str:
    return html.escape(str(value))


def text(x: float, y: float, value: object, size: int = 28, weight: int = 400,
         anchor: str = "start", fill: str = "#111111") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{esc(value)}</text>'
    )


def base(title: str, subtitle: str, number: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="1600" height="900" fill="#ffffff"/>',
        text(90, 90, title, 47, 500),
        text(90, 137, subtitle, 25, 400, fill="#555555"),
        text(1510, 88, number, 26, 500, "end"),
        '<line x1="90" y1="170" x2="1510" y2="170" stroke="#111111" stroke-width="2"/>',
    ]


def finish(parts: list[str], filename: str, source: str) -> None:
    parts.extend([
        '<line x1="90" y1="824" x2="1510" y2="824" stroke="#bbbbbb" stroke-width="1"/>',
        text(90, 861, source, 20, fill="#666666"),
        text(1510, 861, "github.com/saitakarcesme/ram-aware-agents", 20, 500, "end"),
        '</svg>',
    ])
    svg_path = HERE / f"{filename}.svg"
    png_path = HERE / f"{filename}.png"
    svg_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    subprocess.run(
        ["sips", "-s", "format", "png", str(svg_path), "--out", str(png_path)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def render_browser() -> None:
    parts = base(
        "RAM-aware AGENTS.md cut browser-workload memory",
        "8 GB M1 MacBook · React + Playwright · median of 2 quality-valid fresh-project pairs",
        "01 / 02",
    )
    metrics = [
        ("Responsiveness P95", -61.5),
        ("Peak process-tree RSS", -58.9),
        ("P95 process-tree RSS", -57.0),
        ("Average process-tree RSS", -40.6),
        ("Active time", 5.0),
    ]
    zero_x = 860
    scale = 7.3
    parts.extend([
        text(90, 225, "Median change vs control", 25, 500),
        '<line x1="860" y1="255" x2="860" y2="695" stroke="#777777" stroke-width="2"/>',
        text(860, 730, "0%", 20, anchor="middle", fill="#666666"),
        text(465, 770, "less memory / faster", 20, anchor="middle", fill="#666666"),
        text(1060, 770, "more memory / slower", 20, anchor="middle", fill="#666666"),
    ])
    for index, (label, delta) in enumerate(metrics):
        y = 285 + index * 88
        bar_y = y - 31
        end_x = zero_x + delta * scale
        x = min(zero_x, end_x)
        width = abs(end_x - zero_x)
        fill = "#222222" if delta < 0 else "#a8a8a8"
        value_x = end_x + 18
        value_anchor = "start"
        value_fill = "#111111"
        if delta < 0:
            value_x = zero_x - 18
            value_anchor = "end"
            value_fill = "#ffffff"
        parts.extend([
            text(90, y, label, 24, 400),
            f'<rect x="{x:.1f}" y="{bar_y}" width="{width:.1f}" height="42" fill="{fill}"/>',
            text(value_x, y, f"{delta:+.1f}%", 25, 500, value_anchor, value_fill),
        ])
    parts.extend([
        '<line x1="1240" y1="245" x2="1240" y2="700" stroke="#d0d0d0" stroke-width="1"/>',
        text(1285, 295, "Browser processes", 22, fill="#666666"),
        text(1285, 347, "22–24 → 7", 39, 500),
        text(1285, 420, "Minimum free memory", 22, fill="#666666"),
        text(1285, 472, "32–49% → 55–60%", 32, 500),
        text(1285, 558, "Correctness gate", 22, fill="#666666"),
        text(1285, 610, "2 / 2 pairs passed", 30, 500),
        text(1285, 660, "Preliminary: protocol minimum is 3", 19, fill="#666666"),
    ])
    finish(parts, "01-browser-profile", "Source: v2 evidence snapshot · 2026-09-02")


def bar(parts: list[str], x: float, baseline: float, width: float, value: float,
        maximum: float, fill: str, stroke: str, label: str, value_label: str) -> None:
    height = value / maximum * 350
    y = baseline - height
    parts.extend([
        f'<rect x="{x}" y="{y:.1f}" width="{width}" height="{height:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
        text(x + width / 2, y - 14, value_label, 22, 500, "middle"),
        text(x + width / 2, baseline + 34, label, 17, 400, "middle"),
    ])


def render_hook() -> None:
    parts = base(
        "AGENTS.md vs runtime hook",
        "8 GB M1 MacBook · one quality-valid triple per stack · lower is better",
        "02 / 02",
    )
    parts.extend([
        text(90, 225, "Peak process-tree RSS (GiB)", 25, 500),
        text(840, 225, "Active completion time (seconds)", 25, 500),
        '<line x1="775" y1="215" x2="775" y2="735" stroke="#c5c5c5" stroke-width="1"/>',
        '<line x1="115" y1="650" x2="720" y2="650" stroke="#111111" stroke-width="2"/>',
        '<line x1="865" y1="650" x2="1470" y2="650" stroke="#111111" stroke-width="2"/>',
    ])
    styles = {
        "control": ("#ffffff", "#111111"),
        "AGENTS": ("#a8a8a8", "#111111"),
        "hook": ("#222222", "#222222"),
    }
    display = {"control": "Control", "AGENTS": "AGENTS", "hook": "Hook"}
    peak = {
        "Python": [("control", .387558), ("AGENTS", .373306), ("hook", .340027)],
        "Rust": [("control", 1.606537), ("AGENTS", .328613), ("hook", .383331)],
    }
    times = {
        "Python": [("control", 752.223), ("AGENTS", 790.2), ("hook", 720.831)],
        "Rust": [("control", 644.19), ("AGENTS", 748.18), ("hook", 649.842)],
    }
    for group_index, (group, rows) in enumerate(peak.items()):
        group_start = 145 + group_index * 315
        for index, (label, value) in enumerate(rows):
            fill, stroke = styles[label]
            bar(parts, group_start + index * 85, 650, 70, value, 1.8, fill, stroke, display[label], f"{value:.2f}")
        parts.append(text(group_start + 120, 735, group, 23, 500, "middle"))
    for group_index, (group, rows) in enumerate(times.items()):
        group_start = 895 + group_index * 315
        for index, (label, value) in enumerate(rows):
            fill, stroke = styles[label]
            bar(parts, group_start + index * 85, 650, 70, value, 850, fill, stroke, display[label], f"{value:.0f}")
        parts.append(text(group_start + 120, 735, group, 23, 500, "middle"))
    parts.extend([
        text(115, 788, "Rust peak vs control: AGENTS.md −79.5% · hook −76.1%", 21, 500),
        text(865, 788, "Hook vs AGENTS.md: Rust −13.1% · Python −8.8% time", 21, 500),
    ])
    finish(parts, "02-agents-vs-hook", "Source: v3 · 2026-09-04 · quality-valid runs only")


if __name__ == "__main__":
    render_browser()
    render_hook()
