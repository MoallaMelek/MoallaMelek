"""Integration regressions for the offline published-profile audit."""

import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


cards = module("audited_cards", "generate_cards.py")
verify = module("profile_verifier", "verify_profile.py")
NOW = dt.datetime(2026, 11, 8, 12, tzinfo=dt.timezone.utc)


class FrozenDatetime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


CLOCK = SimpleNamespace(datetime=FrozenDatetime, date=dt.date,
                        timezone=dt.timezone, timedelta=dt.timedelta)


class ProfileAuditTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "assets"
            out.mkdir()
            days = [{"date": "2026-10-31", "contributionCount": 20},
                    {"date": "2026-11-08", "contributionCount": 40}]
            stats = {"stars": 2, "commits": 100, "year": 2026,
                     "year_contribs": 100, "prs": 3, "issues": 4, "repos": 5}
            snapshot = {"updated_at": NOW.isoformat(), "user": "MoallaMelek",
                        "stats": stats, "days": days,
                        "streak": cards.streak_metrics(days, NOW.date())}
            (out / "activity-data.json").write_text(json.dumps(snapshot), encoding="utf-8")
            with patch.object(cards, "dt", CLOCK):
                svgs = {"stats": cards.stats_card(stats),
                        "top-langs": cards.langs_card([]),
                        "activity": cards.activity_card(days),
                        "heatmap": cards.heatmap_card(days, NOW.date()),
                        "streak": cards.streak_card(days),
                        "recent-activity": cards.recent_activity_card(days),
                        "activity-updated": cards.frame(
                            900, 42, '<text x="450" y="26">Updated 2026-11-08 12:00 UTC · GitHub contribution calendar</text>')}
            for name, svg in svgs.items():
                (out / f"{name}.svg").write_text(svg, encoding="utf-8")
            readme = "\n".join(
                f'<img src="assets/{name}.svg?v={hashlib.sha256((out / (name + ".svg")).read_bytes()).hexdigest()[:12]}" />'
                for name in svgs)
            (root / "README.md").write_text(readme, encoding="utf-8")
            yield root

    def update_snapshot(self, root, change):
        path = root / "assets/activity-data.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data), encoding="utf-8")


    def test_real_generated_cards_pass_all_checks(self):
        with self.fixture() as root:
            self.assertEqual(verify.audit(root, NOW), [])

    def test_invalid_json_returns_diagnostics(self):
        with self.fixture() as root:
            (root / "assets/activity-data.json").write_text("{", encoding="utf-8")
            self.assertTrue(verify.audit(root, NOW)[0].startswith("input:"))

    def test_boolean_counts_are_reported(self):
        with self.fixture() as root:
            self.update_snapshot(root, lambda data: data["days"][-1].update(contributionCount=True))
            self.assertTrue(any(issue.startswith("calendar.counts:") for issue in verify.audit(root, NOW)))

    def test_date_order_and_uniqueness_are_reported(self):
        for mode in ("duplicate", "reverse"):
            with self.subTest(mode=mode), self.fixture() as root:
                def change(data):
                    if mode == "duplicate":
                        data["days"].append(dict(data["days"][-1]))
                    else:
                        data["days"].reverse()
                self.update_snapshot(root, change)
                label = "calendar.unique:" if mode == "duplicate" else "calendar.order:"
                self.assertTrue(any(issue.startswith(label) for issue in verify.audit(root, NOW)))

    def test_future_contributions_are_reported(self):
        with self.fixture() as root:
            self.update_snapshot(root, lambda data: data["days"].append(
                {"date": "2026-11-09", "contributionCount": 999}))
            self.assertTrue(any(issue.startswith("calendar.future:") for issue in verify.audit(root, NOW)))

    def test_contradictory_streak_lengths_are_reported(self):
        with self.fixture() as root:
            self.update_snapshot(root, lambda data: data["streak"].update(current=10, longest=1))
            self.assertTrue(any(issue.startswith("streak.order:") for issue in verify.audit(root, NOW)))

    def test_changed_asset_requires_a_new_readme_version(self):
        with self.fixture() as root:
            path = root / "assets/activity.svg"
            path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertTrue(any(issue.startswith("readme.cache:") for issue in verify.audit(root, NOW)))

    def test_active_svg_content_is_reported(self):
        with self.fixture() as root:
            path = root / "assets/activity.svg"
            svg = path.read_text(encoding="utf-8")
            path.write_text(svg.replace("</svg>", "<script>unsafe()</script></svg>"), encoding="utf-8")
            self.assertTrue(any(issue.startswith("svg.content:") for issue in verify.audit(root, NOW)))

    def test_cli_reports_success_and_failure(self):
        with self.fixture() as root, patch.object(verify, "dt", CLOCK):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = verify.main(["--root", str(root), "--json"])
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["ok"])
            (root / "assets/streak.svg").unlink()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = verify.main(["--root", str(root), "--json"])
            self.assertEqual(status, 1)
            self.assertFalse(json.loads(output.getvalue())["ok"])
