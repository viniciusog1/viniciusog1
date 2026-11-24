"""Builds the SVGs used by README.md. Standard library only.

Text and layout live here; language mix, last push and CI status come from the
GitHub API. If any request fails nothing is written, so the previous images stay.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path

USER = "viniciusog1"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

THEMES = {
    "dark": dict(bg="#0d1117", panel="#151b23", line="#30363d", ink="#f0f6fc", soft="#9198a1",
                 ok="#3fb950", run="#d29922", on_ok="#0d1117"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", line="#d1d9e0", ink="#1f2328", soft="#59636e",
                  ok="#1a7f37", run="#9a6700", on_ok="#ffffff"),
}

# Each stage is a tool configured in the public repositories listed below.
STAGES = [
    ("Lint", "ruff", "ruff check ."),
    ("Types", "mypy", "mypy app"),
    ("Test", "pytest", "pytest -v"),
    ("Build", "Docker", "docker compose up --build"),
    ("Deploy", "Kubernetes", "kubectl apply -k k8s/"),
    ("Observe", "Grafana", "curl localhost:8000/metrics"),
]

PROJECTS = [
    ("insightpipe", "InsightPipe", "MLOps pipeline for Brazil's power grid",
     ["Ingestion, training, serving, drift checks", "Retraining with a promotion gate"]),
    ("stockguardian", "StockGuardian", "Inventory platform built for operations",
     ["Kubernetes manifests with Kustomize", "Prometheus metrics, OpenTelemetry traces"]),
    ("vox", "Vox", "Self-hosted voice, video and chat",
     ["Peer-to-peer WebRTC on Electron", "Cloudflare tunnel for remote access"]),
    ("pokemon_api", "Pokémon ETL", "From API to dashboard",
     ["Extract and clean with requests and pandas", "Published as a Streamlit app"]),
]

LANG_COLORS = {"Python": "#3572A5", "JavaScript": "#f1e05a", "HTML": "#e34c26", "CSS": "#663399",
               "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384d54", "Shell": "#89e051"}

CYCLE = 14.0   # seconds per loop
STEP = 1.7     # seconds per stage
START = 0.8
OFFSET = START + 6 * STEP + 0.2   # open on the finished pipeline, then loop


# ---------------------------------------------------------------- data

def api(path: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def ci_passing(runs: list[dict]) -> bool:
    """True when the latest finished CI run succeeded."""
    done = [r for r in runs if r.get("name") == "CI" and r.get("status") == "completed"]
    return bool(done) and done[0]["conclusion"] == "success"


def load(repo: str) -> dict:
    base = f"/repos/{USER}/{repo}"
    info = api(base)
    branch = info["default_branch"]
    runs = api(f"{base}/actions/runs?branch={branch}&per_page=20")["workflow_runs"]
    return {"pushed": info["pushed_at"], "languages": api(f"{base}/languages"),
            "ci": ci_passing(runs)}


def shares(languages: dict[str, int], limit: int = 3) -> list[tuple[str, float]]:
    total = sum(languages.values())
    if not total:
        return []
    top = sorted(languages.items(), key=lambda kv: -kv[1])[:limit]
    return [(name, size / total) for name, size in top if size / total >= 0.01]


def month(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %Y")


# ---------------------------------------------------------------- svg

def pct(seconds: float) -> str:
    return f"{seconds / CYCLE * 100:.2f}%"


def stage_css(c: dict) -> str:
    """Without animation every stage reads as passed, so a still frame is complete."""
    css = []
    end = pct(CYCLE - 0.5)
    last = len(STAGES) - 1
    for i in range(len(STAGES)):
        a, b = START + i * STEP, START + i * STEP + STEP - 0.25
        css.append(
            f"@keyframes n{i}{{0%,{pct(a)}{{fill:{c['panel']};stroke:{c['line']}}}"
            f"{pct(a + .15)},{pct(b)}{{fill:{c['panel']};stroke:{c['run']}}}"
            f"{pct(b + .25)},{end}{{fill:{c['ok']};stroke:{c['ok']}}}"
            f"100%{{fill:{c['panel']};stroke:{c['line']}}}}}"
            f"@keyframes k{i}{{0%,{pct(b)}{{opacity:0}}{pct(b + .25)},{end}{{opacity:1}}100%{{opacity:0}}}}"
            f"@keyframes r{i}{{0%,{pct(a)}{{opacity:0}}{pct(a + .15)},{pct(b)}{{opacity:1}}"
            f"{pct(b + .25)},100%{{opacity:0}}}}")
        stop = CYCLE - 0.5 if i == last else a + STEP - 0.05
        css.append(f"@keyframes l{i}{{0%,{pct(a)}{{opacity:0}}{pct(a + .1)},{pct(stop)}{{opacity:1}}"
                   f"{pct(stop + .1)},100%{{opacity:0}}}}")
        css += [f".{part}{i}{{animation:{part}{i} {CYCLE}s linear -{OFFSET:.1f}s infinite}}" for part in "nkrl"]
        if i < last:
            css.append(f"@keyframes w{i}{{0%,{pct(b)}{{stroke-dashoffset:1}}{pct(b + .4)},{end}"
                       f"{{stroke-dashoffset:0}}100%{{stroke-dashoffset:1}}}}"
                       f".w{i}{{animation:w{i} {CYCLE}s linear -{OFFSET:.1f}s infinite}}")
    css.append(".w{stroke-dasharray:1;stroke-dashoffset:0}.r{opacity:0}.l{opacity:0}"
               f".l{last}{{opacity:1}}"
               "@keyframes spin{to{transform:rotate(360deg)}}"
               ".spin{animation:spin 1s linear infinite}"
               "@keyframes blink{50%{opacity:0}}.cur{animation:blink 1s steps(1) infinite}"
               "@media(prefers-reduced-motion:reduce){*{animation:none!important}}")
    return "".join(css)


def node(i: int, x: float, y: float, c: dict) -> str:
    return (
        f'<circle class="n{i}" cx="{x}" cy="{y}" r="17" fill="{c["ok"]}" stroke="{c["ok"]}" stroke-width="2"/>'
        f'<path class="k{i}" d="M{x - 7} {y + .5}l5 5 9.5-10" fill="none" stroke="{c["on_ok"]}" '
        f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<g class="r r{i}"><g transform="translate({x} {y})"><circle class="spin" r="7" fill="none" '
        f'stroke="{c["run"]}" stroke-width="2.6" stroke-dasharray="28 16" stroke-linecap="round"/></g></g>')


def wire(i: int, x1: float, y1: float, x2: float, y2: float, c: dict) -> str:
    d = f"M{x1} {y1}L{x2} {y2}"
    return (f'<path d="{d}" stroke="{c["line"]}" stroke-width="2"/>'
            f'<path class="w w{i}" pathLength="1" d="{d}" stroke="{c["ok"]}" stroke-width="2"/>')


def text(x, y, s, size, fill, weight=400, anchor="start", font=SANS, cls="") -> str:
    attr = f' class="{cls}"' if cls else ""
    return (f'<text{attr} x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def frame(w: int, h: int, title: str, body: str, c: dict, css: str = "") -> str:
    style = f"<style>{css}</style>" if css else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f"<title>{escape(title)}</title>{style}"
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["bg"]}" stroke="{c["line"]}"/>'
            f"{body}</svg>\n")


TITLE = ("Vinícius Oliveira, from data to DevOps. Animated pipeline: "
         + ", ".join(s[0].lower() for s in STAGES) + ".")


def hero(c: dict) -> str:
    out = [text(40, 74, "Vinícius Oliveira", 40, c["ink"], 700),
           text(40, 110, "From data to DevOps: build it, test it, watch it run.", 19, c["soft"])]
    xs, y = [84 + i * 134.4 for i in range(len(STAGES))], 182
    for i in range(len(xs) - 1):
        out.append(wire(i, xs[i] + 24, y, xs[i + 1] - 24, y, c))
    for i, (name, tool, _) in enumerate(STAGES):
        out += [node(i, xs[i], y, c), text(xs[i], y + 43, name, 16, c["ink"], 600, "middle"),
                text(xs[i], y + 63, tool, 13.5, c["soft"], 400, "middle", MONO)]
    out.append(f'<rect x="40" y="276" width="760" height="44" rx="6" fill="{c["panel"]}"/>')
    out.append(text(58, 303, "$", 15, c["ok"], 700, font=MONO))
    out += [text(78, 303, cmd, 15, c["ink"], font=MONO, cls=f"l l{i}") for i, (_, _, cmd) in enumerate(STAGES)]
    out.append(f'<rect class="cur" x="776" y="289" width="8" height="18" fill="{c["soft"]}"/>')
    return frame(840, 348, TITLE, "".join(out), c, stage_css(c))


def hero_small(c: dict) -> str:
    out = [text(24, 56, "Vinícius Oliveira", 32, c["ink"], 700),
           text(24, 90, "From data to DevOps:", 18, c["soft"]),
           text(24, 114, "build it, test it, watch it run.", 18, c["soft"])]
    x, ys = 45, [164 + i * 58 for i in range(len(STAGES))]
    for i in range(len(ys) - 1):
        out.append(wire(i, x, ys[i] + 22, x, ys[i + 1] - 22, c))
    for i, (name, tool, _) in enumerate(STAGES):
        out += [node(i, x, ys[i], c), text(80, ys[i] + 6, name, 18, c["ink"], 600),
                text(376, ys[i] + 6, tool, 16, c["soft"], 400, "end", MONO)]
    return frame(400, 492, TITLE, "".join(out), c, stage_css(c))


def card(name: str, tagline: str, points: list[str], data: dict, c: dict) -> str:
    w, pad = 414, 24
    out = [text(pad, 46, name, 22, c["ink"], 700)]
    if data["ci"]:
        out.append(f'<circle cx="{w - pad - 82}" cy="39" r="5" fill="{c["ok"]}"/>'
                   + text(w - pad, 44, "CI passing", 14, c["ok"], 600, "end"))
    out.append(text(pad, 74, tagline, 16, c["ink"]))
    for i, point in enumerate(points):
        out.append(text(pad, 106 + i * 25, point, 15, c["soft"]))
    mix = shares(data["languages"])
    span, x = w - 2 * pad, float(pad)
    out.append(f'<clipPath id="b"><rect x="{pad}" y="154" width="{span}" height="6" rx="3"/></clipPath>'
               f'<g clip-path="url(#b)"><rect x="{pad}" y="154" width="{span}" height="6" fill="{c["line"]}"/>')
    for lang, share in mix:
        out.append(f'<rect x="{x:.1f}" y="154" width="{share * span:.1f}" height="6" '
                   f'fill="{LANG_COLORS.get(lang, c["soft"])}"/>')
        x += share * span
    out.append("</g>")
    label = "  ·  ".join(f"{lang} {share:.0%}" for lang, share in mix[:2])
    out += [text(pad, 187, label, 14, c["soft"]),
            text(w - pad, 187, month(data["pushed"]), 14, c["soft"], 400, "end")]
    return frame(w, 208, f"{name}: {tagline}. {'. '.join(points)}.", "".join(out), c)


def build(data: dict[str, dict]) -> dict[str, str]:
    files = {}
    for theme, c in THEMES.items():
        files[f"hero-{theme}.svg"] = hero(c)
        files[f"hero-small-{theme}.svg"] = hero_small(c)
        for repo, name, tagline, points in PROJECTS:
            files[f"{repo}-{theme}.svg"] = card(name, tagline, points, data[repo], c)
    return files


def main() -> int:
    data = {repo: load(repo) for repo, *_ in PROJECTS}
    files = build(data)
    ASSETS.mkdir(exist_ok=True)
    for name, svg in files.items():
        (ASSETS / name).write_text(svg, encoding="utf-8", newline="\n")
    print(f"{len(files)} files written to {ASSETS.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
