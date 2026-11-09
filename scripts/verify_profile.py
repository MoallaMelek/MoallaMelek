"""Audit published profile assets offline, without changing any files.

Run: python scripts/verify_profile.py
Exit status is zero only when all checks pass. No token or network is used.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"s": "http://www.w3.org/2000/svg"}
REQUIRED = ("stats", "top-langs", "activity", "heatmap", "streak",
            "recent-activity", "activity-updated")
CHECKS = []


def check(label):
    def register(function):
        CHECKS.append((label, function))
        return function
    return register


def count(value):
    return type(value) is int and value >= 0


class Context:
    def __init__(self, root, now):
        self.root = Path(root).resolve()
        self.now = now
        self.data = json.loads(self.path("assets/activity-data.json").read_text(encoding="utf-8"))
        self.readme = self.path("README.md").read_text(encoding="utf-8")

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Asset resolves outside the repository")
        return path

    def timestamp(self):
        return dt.datetime.fromisoformat(self.data["updated_at"].replace("Z", "+00:00"))

    def days(self):
        return self.data["days"]

    def dates(self):
        return [dt.date.fromisoformat(day["date"]) for day in self.days()]

    def active(self):
        return {dt.date.fromisoformat(day["date"]) for day in self.days()
                if day["contributionCount"] > 0}

    def svg(self, name):
        return ET.fromstring(self.path(f"assets/{name}.svg").read_text(encoding="utf-8"))

    def images(self):
        return re.findall(r"(assets/[A-Za-z0-9_-]+\.svg)(?:\?v=([A-Za-z0-9_-]+))?", self.readme)


def audit(root, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        context = Context(root, now)
    except (OSError, ValueError) as error:
        return [f"input: cannot read snapshot or README ({type(error).__name__})"]
    issues = []
    for label, function in CHECKS:
        try:
            valid = function(context)
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, ET.ParseError) as error:
            issues.append(f"{label}: invalid or missing data ({type(error).__name__})")
        else:
            if not valid:
                issues.append(label)
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="Print a machine-readable audit result")
    args = parser.parse_args(argv)
    issues = audit(args.root)
    if args.json:
        print(json.dumps({"ok": not issues, "checks": len(CHECKS), "issues": issues}, indent=2))
    elif issues:
        for issue in issues:
            print(f"FAIL: {issue}")
    else:
        print(f"PASS: {len(CHECKS)} profile checks")
    return 1 if issues else 0


@check("snapshot.user: expected a nonempty GitHub login")
def user_login(context):
    return isinstance(context.data["user"], str) and bool(re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", context.data["user"]))

@check("snapshot.timestamp: expected an aware UTC timestamp")
def utc_timestamp(context):
    stamp = context.timestamp()
    return stamp.tzinfo is not None and stamp.utcoffset() == dt.timedelta(0)

@check("snapshot.timestamp: refresh time is in the future")
def timestamp_not_future(context):
    return context.timestamp() <= context.now + dt.timedelta(minutes=5)

@check("calendar.days: expected a nonempty list")
def calendar_list(context):
    return isinstance(context.days(), list) and bool(context.days())

@check("calendar.records: missing date or contributionCount")
def calendar_records(context):
    return all(isinstance(day, dict) and {"date", "contributionCount"} <= day.keys()
               for day in context.days())

@check("calendar.dates: expected ISO calendar dates")
def canonical_dates(context):
    return all(isinstance(day["date"], str) and
               dt.date.fromisoformat(day["date"]).isoformat() == day["date"]
               for day in context.days())

@check("calendar.order: dates must be chronological")
def chronological_dates(context):
    dates = context.dates()
    return dates == sorted(dates)

@check("calendar.unique: duplicate dates found")
def unique_dates(context):
    dates = context.dates()
    return len(dates) == len(set(dates))

@check("calendar.counts: expected nonnegative integer counts")
def contribution_counts(context):
    return all(count(day["contributionCount"]) for day in context.days())

@check("calendar.future: dates extend past the refresh day")
def no_future_dates(context):
    return all(date <= context.timestamp().date() for date in context.dates())

@check("calendar.today: final date does not match refresh day")
def final_date(context):
    return context.dates()[-1] == context.timestamp().date()

@check("stats: expected an object")
def statistics_object(context):
    return isinstance(context.data["stats"], dict)

@check("stats.counts: expected nonnegative integer counters")
def statistics_counts(context):
    return all(count(context.data["stats"][key])
               for key in ("stars", "commits", "year_contribs", "prs", "issues", "repos"))

@check("stats.year: year does not match refresh timestamp")
def statistics_year(context):
    year = context.data["stats"]["year"]
    return type(year) is int and year == context.timestamp().year

@check("streak: expected an object")
def streak_object(context):
    return isinstance(context.data["streak"], dict)

@check("streak.counts: expected nonnegative integer metrics")
def streak_counts(context):
    return all(count(context.data["streak"][key])
               for key in ("current", "longest", "active_days"))

@check("streak.order: expected current <= longest <= active days")
def streak_order(context):
    metrics = context.data["streak"]
    return metrics["current"] <= metrics["longest"] <= metrics["active_days"]

@check("streak.active: lifetime active days are smaller than visible history")
def visible_active_days(context):
    return context.data["streak"]["active_days"] >= len(context.active())

@check("streak.current: activity near today contradicts current streak")
def current_streak_activity(context):
    today = context.timestamp().date()
    active = context.active()
    expected = today in active or today - dt.timedelta(days=1) in active
    return (context.data["streak"]["current"] > 0) == expected

@check("streak.length: current streak is smaller than visible consecutive history")
def visible_streak_length(context):
    today = context.timestamp().date()
    active = context.active()
    cursor = today if today in active else today - dt.timedelta(days=1)
    visible = 0
    while cursor in active:
        visible += 1
        cursor -= dt.timedelta(days=1)
    return context.data["streak"]["current"] >= visible

@check("svg.files: expected all generated cards to be valid SVG")
def svg_files(context):
    return all(context.svg(name).tag == "{http://www.w3.org/2000/svg}svg"
               for name in REQUIRED)

@check("svg.roles: generated cards must expose the image role")
def svg_roles(context):
    return all(context.svg(name).get("role") == "img" for name in REQUIRED)

@check("svg.activity: expected the existing 900 by 280 canvas")
def activity_dimensions(context):
    root = context.svg("activity")
    return (root.get("width"), root.get("height"), root.get("viewBox")) == (
        "900", "280", "0 0 900 280")

@check("svg.heatmap: expected the existing 900 by 180 canvas")
def heatmap_dimensions(context):
    root = context.svg("heatmap")
    return (root.get("width"), root.get("height"), root.get("viewBox")) == (
        "900", "180", "0 0 900 180")

@check("svg.palette: calendar cells must use the existing green palette")
def heatmap_palette(context):
    cells = [node for node in context.svg("heatmap").findall("s:rect", NS)
             if node.get("data-date")]
    palette = {"#161B22", "#0E4429", "#006D32", "#26A641", "#39D353"}
    return bool(cells) and all(node.get("fill") in palette for node in cells)

@check("svg.content: script, embedded HTML, or event handlers found")
def svg_active_content(context):
    for name in REQUIRED:
        for node in context.svg(name).iter():
            if node.tag.rsplit("}", 1)[-1].lower() in {"script", "foreignobject"}:
                return False
            if any(key.rsplit("}", 1)[-1].lower().startswith("on") for key in node.attrib):
                return False
    return True

@check("readme.cache: local card hashes do not match SVG contents")
def image_versions(context):
    images = context.images()
    return bool(images) and all(version == hashlib.sha256(
        context.path(path).read_bytes()).hexdigest()[:12] for path, version in images)

@check("readme.paths: referenced assets must resolve inside the repository")
def local_asset_paths(context):
    return all((context.root / path).resolve().is_relative_to(context.root)
               for path, version in context.images())

@check("svg.today: heatmap tooltip does not match the snapshot count")
def heatmap_today(context):
    latest = context.days()[-1]
    for cell in context.svg("heatmap").findall("s:rect", NS):
        if cell.get("data-date") == latest["date"]:
            title = cell.find("s:title", NS)
            return title is not None and title.text == (
                f"{latest['date']}: {latest['contributionCount']} contributions")
    return False

@check("svg.streak: rendered values do not match snapshot metrics")
def rendered_streak(context):
    root = context.svg("streak")
    values = {node.get("x"): node.text for node in root.findall("s:text", NS)
              if node.get("y") == "90"}
    metrics = context.data["streak"]
    return values == {"150": f"{metrics['active_days']:,}",
                      "450": f"{metrics['current']:,}", "750": f"{metrics['longest']:,}"}


def stats_value(context, label):
    for group in context.svg("stats").findall("s:g", NS):
        label_node = group.find("s:text[@class='label']", NS)
        if label_node is not None and label_node.text == label + ":":
            value = group.find("s:text[@class='value']", NS)
            return value.text if value is not None else None
    return None


@check("stats.rendered.commits: SVG value disagrees with the snapshot")
def commit_total(context):
    stats = context.data["stats"]
    return stats_value(context, "Total commits") == f"{stats['commits']:,}"


@check("stats.rendered.stars: SVG value disagrees with the snapshot")
def star_total(context):
    stats = context.data["stats"]
    return stats_value(context, "Total stars earned") == f"{stats['stars']:,}"


@check("stats.rendered.prs: SVG value disagrees with the snapshot")
def pull_request_total(context):
    stats = context.data["stats"]
    return stats_value(context, "Pull requests") == f"{stats['prs']:,}"


@check("stats.rendered.issues: SVG value disagrees with the snapshot")
def issue_total(context):
    stats = context.data["stats"]
    return stats_value(context, "Issues opened") == f"{stats['issues']:,}"


@check("stats.rendered.repos: SVG value disagrees with the snapshot")
def repository_total(context):
    stats = context.data["stats"]
    return stats_value(context, "Public repositories") == f"{stats['repos']:,}"


@check("stats.rendered.year_contribs: SVG value disagrees with the snapshot")
def annual_total(context):
    stats = context.data["stats"]
    return stats_value(context, f"Contributions ({stats['year']})") == f"{stats['year_contribs']:,}"


def card_text(context, card, x, y):
    node = context.svg(card).find(f"s:text[@x='{x}'][@y='{y}']", NS)
    return node.text if node is not None else None


def window_days(context, length):
    first = context.timestamp().date() - dt.timedelta(days=length - 1)
    return [day for day in context.days() if day["date"] >= first.isoformat()]


@check("recent.today: card total disagrees with the snapshot")
def recent_today(context):
    total = sum(day["contributionCount"] for day in window_days(context, 1))
    return card_text(context, "recent-activity", 150, 84) == f"{total:,}"


@check("recent.week: card total disagrees with the snapshot")
def recent_week(context):
    total = sum(day["contributionCount"] for day in window_days(context, 7))
    return card_text(context, "recent-activity", 450, 84) == f"{total:,}"


@check("recent.month: card total disagrees with the snapshot")
def recent_month(context):
    total = sum(day["contributionCount"] for day in window_days(context, 31))
    return card_text(context, "recent-activity", 750, 84) == f"{total:,}"


@check("recent.active: caption disagrees with the snapshot")
def recent_active(context):
    active = sum(day["contributionCount"] > 0 for day in window_days(context, 31))
    caption = card_text(context, "recent-activity", 450, 145) or ""
    return caption.startswith(f"{active} active days in the last 31 days")


def heatmap_cells(context):
    return [cell for cell in context.svg("heatmap").findall("s:rect", NS)
            if cell.get("data-date")]


@check("heatmap.dates: expected 365 consecutive dates ending on the snapshot date")
def heatmap_dates(context):
    end = context.timestamp().date()
    dates = [(end - dt.timedelta(days=offset)).isoformat() for offset in range(364, -1, -1)]
    return [cell.get("data-date") for cell in heatmap_cells(context)] == dates


@check("heatmap.counts: a shared date shows an incorrect count")
def heatmap_counts(context):
    known = {day["date"]: day["contributionCount"] for day in context.days()}
    for cell in heatmap_cells(context):
        date = cell.get("data-date")
        if date in known:
            title = cell.find("s:title", NS)
            if title is None or title.text != f"{date}: {known[date]} contributions":
                return False
    return True


@check("heatmap.inactive: zero-count cells must use the inactive color")
def heatmap_inactive(context):
    for cell in heatmap_cells(context):
        title = cell.find("s:title", NS)
        if title is None or title.text is None:
            return False
        inactive = title.text.endswith(": 0 contributions")
        if (cell.get("fill") == "#161B22") != inactive:
            return False
    return True


@check("refresh.label: timestamp card disagrees with the snapshot")
def refresh_label(context):
    label = card_text(context, "activity-updated", 450, 26) or ""
    stamp = context.timestamp().strftime("%Y-%m-%d %H:%M UTC")
    return label.startswith(f"Updated {stamp} ·")


CURVE_START = dt.date(2026, 9, 26)


def curve_points(context):
    line = context.svg("activity").find("s:polyline", NS)
    if line is None:
        return []
    return [tuple(float(value) for value in point.split(","))
            for point in line.get("points", "").split()]


@check("curve.bounds: a point is missing or lies outside the plot")
def curve_bounds(context):
    points = curve_points(context)
    if not points:
        return context.timestamp().date() < CURVE_START
    return all(50 <= x <= 875 and 55 <= y <= 235 for x, y in points)


@check("curve.dots: markers disagree with the plotted points")
def curve_dots(context):
    dots = context.svg("activity").findall("s:circle", NS)
    positions = [(float(dot.get("cx")), float(dot.get("cy"))) for dot in dots]
    return positions == curve_points(context)


if __name__ == "__main__":
    raise SystemExit(main())
