"""Generate the SVG cards used by the profile README.

Replaces the public github-readme-stats / activity-graph Vercel instances,
which are paused. Runs in GitHub Actions (see .github/workflows/cards.yml)
using only the standard library.
"""

import datetime as dt
import hashlib
import json
import os
import re
import textwrap
import urllib.request
from html import escape
from pathlib import Path

USER = os.environ.get("GH_USER", "MoallaMelek")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets"
PINNED = [
    "Reward-Goblin",
    "Hydra-Agent-Orchestrator",
    "Reinforcement-Learning-Memory-Dungeon",
    "Vector-CS",
    "Deep-Learning-Plant-DNA-Optimization",
    "AI-Driven-Therapeutic-Protein-Plant-Synthesis",
    "Real-Time-Payment-Observability-Dashboard",
    "Telekinesis-CV",
    "Festy-Event",
    "LogiXpress-WebSite",
]
# Linguist misclassifications / tooling noise that shouldn't count as "languages I use".
IGNORED_LANGS = {"Hack", "Batchfile", "Objective-C"}

BG, BORDER = "#0D1117", "#30363D"
TITLE, TEXT, MUTED, ACCENT, ICON = "#58A6FF", "#C9D1D9", "#8B949E", "#2563EB", "#7EE787"
FONT = "font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        name description stargazerCount forkCount
        primaryLanguage { name color }
        languages(first: 20) { edges { size node { name color } } }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def graphql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def all_time_commits(created_at):
    """contributionsCollection spans at most one year, so sum per calendar year."""
    q = """query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) { contributionsCollection(from: $from, to: $to) { totalCommitContributions } } }"""
    now = dt.datetime.now(dt.timezone.utc)
    total = 0
    for year in range(created_at.year, now.year + 1):
        start = max(created_at, dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc))
        end = min(now, dt.datetime(year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc))
        data = graphql(q, {"login": USER, "from": start.isoformat(), "to": end.isoformat()})
        total += data["user"]["contributionsCollection"]["totalCommitContributions"]
    return total


def frame(width, height, body, title=None):
    head = ""
    if title:
        head = f'<text x="25" y="35" class="title">{escape(title)}</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img">
<style>
  text {{ {FONT}; }}
  .title {{ font-size: 18px; font-weight: 600; fill: {TITLE}; }}
  .label {{ font-size: 14px; fill: {TEXT}; }}
  .value {{ font-size: 14px; font-weight: 700; fill: {TEXT}; }}
  .muted {{ font-size: 12px; fill: {MUTED}; }}
  .fade {{ opacity: 0; animation: fade .5s ease-in-out forwards; }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
</style>
<rect x="0.5" y="0.5" rx="10" width="{width - 1}" height="{height - 1}" fill="{BG}" stroke="{BORDER}"/>
{head}
{body}
</svg>
"""


# Octicon paths (MIT, github/primer)
ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
    "fork": "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z",
    "flame": "M9.533.753V.752c.217 2.385 1.463 3.626 2.653 4.81C13.37 6.74 14.498 7.863 14.498 10c0 3.5-3 6-6.5 6S1.5 13.512 1.5 10c0-1.298.536-2.56 1.425-3.286.235-.192.567-.003.629.293.264 1.267 1.143 2.328 2.279 2.681.182.057.32-.13.303-.318-.221-2.345.221-4.692 1.584-6.573.618-.851 1.279-1.567 1.813-2.044Z",
}


def icon(name, x, y, color=ICON):
    return f'<svg x="{x}" y="{y}" width="16" height="16" viewBox="0 0 16 16"><path fill="{color}" d="{ICONS[name]}"/></svg>'


def stats_card(stats):
    rows = [
        ("star", "Total stars earned", stats["stars"]),
        ("commit", "Total commits", stats["commits"]),
        ("flame", f"Contributions ({stats['year']})", stats["year_contribs"]),
        ("pr", "Pull requests", stats["prs"]),
        ("issue", "Issues opened", stats["issues"]),
        ("repo", "Public repositories", stats["repos"]),
    ]
    body = []
    for i, (ic, label, value) in enumerate(rows):
        y = 60 + i * 25
        body.append(
            f'<g class="fade" style="animation-delay:{150 + i * 120}ms">'
            f'{icon(ic, 25, y)}<text x="50" y="{y + 12.5}" class="label">{label}:</text>'
            f'<text x="240" y="{y + 12.5}" class="value">{value:,}</text></g>'
        )
    return frame(420, 225, "\n".join(body), f"{USER}'s GitHub Stats")


def langs_card(langs):
    total = sum(v["size"] for v in langs) or 1
    langs = langs[:8]
    x, bar = 25, []
    bar.append('<clipPath id="bar"><rect x="25" y="55" width="330" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    for lang in langs:
        w = 330 * lang["size"] / total
        bar.append(f'<rect x="{x:.2f}" y="55" width="{w + 0.5:.2f}" height="8" fill="{lang["color"]}"/>')
        x += w
    bar.append("</g>")
    items = []
    for i, lang in enumerate(langs):
        col, row = i % 2, i // 2
        lx, ly = 25 + col * 170, 90 + row * 30
        pct = 100 * lang["size"] / total
        items.append(
            f'<g class="fade" style="animation-delay:{150 + i * 100}ms">'
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{lang["color"]}"/>'
            f'<text x="{lx + 16}" y="{ly}" class="label">{escape(lang["name"])} <tspan class="muted">{pct:.1f}%</tspan></text></g>'
        )
    return frame(380, 225, "\n".join(bar + items), "Most Used Languages")


def pin_card(repo):
    lang = repo["primaryLanguage"] or {"name": "Markdown", "color": MUTED}
    lines = textwrap.wrap(repo["description"] or "", 58)[:3]
    if len(textwrap.wrap(repo["description"] or "", 58)) > 3:
        lines[-1] = lines[-1].rstrip(".,; ") + "…"
    desc = "".join(
        f'<tspan x="25" dy="{0 if i == 0 else 18}">{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    name = repo["name"]
    name_size = min(16, 355 / (len(name) * 0.58))  # shrink long names to fit the card
    body = f"""
{icon("repo", 25, 21, MUTED)}
<text x="48" y="34" class="title" style="font-size:{name_size:.1f}px">{escape(name)}</text>
<text x="25" y="62" class="muted" style="font-size:13px;fill:{TEXT}">{desc}</text>
<circle cx="31" cy="126" r="6" fill="{lang['color'] or MUTED}"/>
<text x="43" y="130.5" class="muted">{escape(lang['name'])}</text>
{icon("star", 150, 118, MUTED)}<text x="171" y="130.5" class="muted">{repo['stargazerCount']}</text>
{icon("fork", 205, 118, MUTED)}<text x="226" y="130.5" class="muted">{repo['forkCount']}</text>
"""
    return frame(420, 150, body)


def activity_card(days):
    days = days[-31:]
    w, h, left, right, top, bottom = 900, 280, 50, 25, 55, 45
    pw, ph = w - left - right, h - top - bottom
    peak = max(4, max(d["contributionCount"] for d in days))
    step = -(-peak // 4)  # ceil
    peak = step * 4
    pts = [
        (left + i * pw / (len(days) - 1), top + ph - ph * d["contributionCount"] / peak)
        for i, d in enumerate(days)
    ]
    grid = []
    for k in range(5):
        y = top + ph - ph * k / 4
        grid.append(f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>')
        grid.append(f'<text x="{left - 10}" y="{y + 4:.1f}" class="muted" text-anchor="end">{step * k}</text>')
    for i, d in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            date = dt.date.fromisoformat(d["date"])
            grid.append(
                f'<text x="{pts[i][0]:.1f}" y="{h - 20}" class="muted" text-anchor="middle">{date.strftime("%b %d")}</text>'
            )
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{left},{top + ph} {line} {w - right},{top + ph}"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ICON}"/>' for x, y in pts)
    total = sum(d["contributionCount"] for d in days)
    body = f"""
<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{TITLE}" stop-opacity=".35"/><stop offset="1" stop-color="{TITLE}" stop-opacity="0"/>
</linearGradient></defs>
<text x="{w - 25}" y="35" class="muted" text-anchor="end">{total} contributions in the last 31 days</text>
{''.join(grid)}
<polygon points="{area}" fill="url(#area)"/>
<polyline points="{line}" stroke="{TITLE}" stroke-width="2.5" stroke-linejoin="round" fill="none"/>
{dots}
"""
    return frame(w, h, body, "Contribution Activity")


def refresh_card_links():
    """Change image URLs only when their generated contents change."""
    readme = OUT.parent / "README.md"
    content = readme.read_text(encoding="utf-8")
    def version(match):
        path = match.group(1)
        digest = hashlib.sha256((OUT.parent / path).read_bytes()).hexdigest()[:12]
        return f"{path}?v={digest}"
    content = re.sub(r"(assets/(?:stats|top-langs|activity)\.svg)(?:\?v=[A-Za-z0-9_-]+)?", version, content)
    readme.write_text(content, encoding="utf-8")


def main():
    if not TOKEN:
        raise SystemExit("Set GH_TOKEN or GITHUB_TOKEN")
    now = dt.datetime.now(dt.timezone.utc)
    data = graphql(
        QUERY,
        {"login": USER, "from": (now - dt.timedelta(days=365)).isoformat(), "to": now.isoformat()},
    )["user"]
    repos = [r for r in data["repositories"]["nodes"] if r["name"] != USER]
    created = dt.datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00"))
    year_start = dt.datetime(now.year, 1, 1, tzinfo=dt.timezone.utc)
    year_data = graphql(
        """query($login: String!, $from: DateTime!, $to: DateTime!) { user(login: $login) {
          contributionsCollection(from: $from, to: $to) { contributionCalendar { totalContributions } } } }""",
        {"login": USER, "from": year_start.isoformat(), "to": now.isoformat()},
    )["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    stats = {
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": all_time_commits(created),
        "year": now.year,
        "year_contribs": year_data,
        "prs": data["pullRequests"]["totalCount"],
        "issues": data["issues"]["totalCount"],
        "repos": len(repos),
    }

    sizes = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in IGNORED_LANGS:
                continue
            entry = sizes.setdefault(name, {"name": name, "color": edge["node"]["color"] or MUTED, "size": 0})
            entry["size"] += edge["size"]
    langs = sorted(sizes.values(), key=lambda l: l["size"], reverse=True)

    days = [d for w in data["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]

    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(stats_card(stats), encoding="utf-8")
    (OUT / "top-langs.svg").write_text(langs_card(langs), encoding="utf-8")
    (OUT / "activity.svg").write_text(activity_card(days), encoding="utf-8")
    by_name = {r["name"]: r for r in repos}
    for name in PINNED:
        if name in by_name:
            (OUT / f"pin-{name}.svg").write_text(pin_card(by_name[name]), encoding="utf-8")
    refresh_card_links()
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
