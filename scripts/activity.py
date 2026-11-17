#!/usr/bin/env python3
"""Draw the contribution calendar as an Abyssal "sonar" heatmap SVG.

Usage:
  GITHUB_TOKEN=... python3 scripts/activity.py --user praddy-31 --out dist/activity.svg
  python3 scripts/activity.py --sample --out assets/preview/activity.svg   (made-up data, for the local preview)

Standard library only, so it runs on a bare GitHub runner. The token is read from the environment and never printed.
Contribution levels come from GitHub's own quartiles (contributionLevel), drawn as light in the dark: no count,
no totals (owner's choice: just the heatmap). A sonar line sweeps across the year.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import urllib.request

LEVEL = {  # Abyssal Trench only: dark water -> bioluminescence
    "NONE": "#0e1c29",
    "FIRST_QUARTILE": "#143349",
    "SECOND_QUARTILE": "#3fbdc9",
    "THIRD_QUARTILE": "#4fe3c1",
    "FOURTH_QUARTILE": "#dcebf3",
}
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
weeks{contributionDays{date contributionLevel}}}}}}"""


def fetch(user):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-activity-svg"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit("GitHub API error: " + "; ".join(e.get("message", "?") for e in body["errors"]))
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[d["contributionLevel"] for d in w["contributionDays"]] for w in weeks]


def sample():
    rnd = random.Random(31)
    keys = list(LEVEL)
    weeks = []
    for w in range(53):
        busy = 0.25 + 0.6 * (w / 52)  # gets busier towards today
        weeks.append([keys[min(4, int(rnd.random() ** (1.6 - busy) * 4.6))] if rnd.random() < busy else "NONE"
                      for _ in range(7)])
    return weeks


def render(weeks):
    cell, gap, pad = 12, 2, 16
    W = 800
    grid_w = len(weeks) * (cell + gap) - gap
    x0 = (W - grid_w) // 2
    H = pad * 2 + 7 * (cell + gap) - gap + 8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'shape-rendering="crispEdges" role="img"><title>Contributions, last 12 months</title>'
           f'<desc>Contribution heatmap: darker water means fewer contributions, brighter glow means more.</desc>',
           f'<rect width="{W}" height="{H}" fill="#06101a"/>',
           f'<rect x="0" y="0" width="8" height="{H}" fill="#4fe3c1"/>']
    for i, week in enumerate(weeks):
        for j, lv in enumerate(week):
            out.append(f'<rect x="{x0 + i*(cell+gap)}" y="{pad + j*(cell+gap)}" width="{cell}" height="{cell}" '
                       f'fill="{LEVEL.get(lv, LEVEL["NONE"])}"/>')
    # sonar sweep: a soft vertical beam crossing the year every 8 s
    gh = 7 * (cell + gap) - gap
    out.append(f'<g opacity="0.35"><rect x="0" y="{pad-4}" width="4" height="{gh+8}" fill="#4fe3c1"/>'
               f'<rect x="-8" y="{pad-4}" width="8" height="{gh+8}" fill="#4fe3c1" opacity="0.4"/>'
               f'<animateTransform attributeName="transform" type="translate" from="{x0-12} 0" '
               f'to="{x0+grid_w+12} 0" dur="8s" repeatCount="indefinite"/></g>')
    # legend: five steps of light, bottom right
    lx = W - pad - 5 * 14
    for k, col in enumerate(LEVEL.values()):
        out.append(f'<rect x="{lx + k*14}" y="{H-12}" width="10" height="6" fill="{col}"/>')
    out.append("</svg>\n")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    weeks = sample() if a.sample else fetch(a.user or sys.exit("--user is required"))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as fh:
        fh.write(render(weeks))
    print(f"wrote {a.out} ({len(weeks)} weeks)")


if __name__ == "__main__":
    main()
