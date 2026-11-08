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


if __name__ == "__main__":
    raise SystemExit(main())
