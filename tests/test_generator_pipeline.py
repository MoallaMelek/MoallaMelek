"""Offline API and end-to-end generation regressions for profile cards."""

import datetime as dt
import importlib.util
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "pipeline_cards", Path(__file__).parents[1] / "scripts" / "generate_cards.py"
)
cards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cards)
NS = {"s": "http://www.w3.org/2000/svg"}
NOW = dt.datetime(2026, 10, 31, 12, 0, tzinfo=dt.timezone.utc)
README = """<div align="center">
<img height="180" src="assets/stats.svg?v=old" alt="Stats" />
<img width="100%" src="assets/activity.svg?v=old" alt="Activity" />
<img src="assets/activity-updated.svg?v=old" alt="Updated" />
<img src="https://streak-stats.demolab.com?user=MoallaMelek&v=old" alt="Streak" />
</div>
"""


class FrozenDatetime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


CLOCK = SimpleNamespace(datetime=FrozenDatetime, date=dt.date,
                        timezone=dt.timezone, timedelta=dt.timedelta)


def day(date, count):
    return {"date": date, "contributionCount": count}


def collection(commits, days):
    return {"user": {"contributionsCollection": {
        "totalCommitContributions": commits,
        "contributionCalendar": {"weeks": [{"contributionDays": days}]}
    }}}


def repo(name, languages):
    return {"name": name, "description": "A sample repository",
            "stargazerCount": 2, "forkCount": 1,
            "primaryLanguage": {"name": "Python", "color": "#3572A5"},
            "languages": {"edges": [
                {"size": size, "node": {"name": lang, "color": "#3572A5"}}
                for lang, size in languages
            ]}}


class GeneratorPipelineTests(unittest.TestCase):
    def history(self):
        created = dt.datetime(2024, 6, 15, 9, 30, tzinfo=dt.timezone.utc)
        responses = [
            collection(5, [day("2024-01-01", 99), day("2024-06-15", 2),
                           day("2024-12-31", 3), day("2025-01-01", 5)]),
            collection(11, [day("2024-12-31", 3), day("2025-01-01", 5),
                            day("2025-12-31", 6)]),
            collection(40, [day("2025-12-31", 6), day("2026-10-30", 20),
                            day("2026-10-31", 20), day("2026-11-01", 99)]),
        ]
        with patch.object(cards, "dt", CLOCK), patch.object(
                cards, "graphql", side_effect=responses) as request:
            result = cards.all_time_activity(created)
        return result, request.call_args_list

    def generate(self, check, repositories=None):
        if repositories is None:
            repositories = [
                repo(cards.USER, [("Python", 9999)]),
                repo("Reward-Goblin", [("Python", 100), ("Hack", 999)]),
                repo("Another-Project", [("Python", 300), ("JavaScript", 100)])
            ]
        days = [day("2026-10-30", 20), day("2026-10-31", 20),
                day("2026-11-01", 999)]
        data = {
            "createdAt": "2024-01-01T00:00:00Z",
            "repositories": {"nodes": repositories},
            "pullRequests": {"totalCount": 3}, "issues": {"totalCount": 4},
            "contributionsCollection": {
                "contributionCalendar": {"weeks": [{"contributionDays": days}]}
            },
        }
        year = {"user": {"contributionsCollection": {
            "contributionCalendar": {"totalContributions": 100}}}}
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            out = root / "assets"
            (root / "README.md").write_text(README, encoding="utf-8")
            stack.enter_context(patch.object(cards, "OUT", out))
            stack.enter_context(patch.object(cards, "TOKEN", "offline-fixture"))
            stack.enter_context(patch.object(cards, "dt", CLOCK))
            stack.enter_context(patch.object(cards, "graphql",
                                             side_effect=[{"user": data}, year]))
            stack.enter_context(patch.object(cards, "all_time_activity",
                                             return_value=(432, days)))
            stack.enter_context(patch("builtins.print"))
            cards.main()
            check(root, out)


    def test_graphql_returns_only_the_data_payload(self):
        body = {"data": {"user": {"name": "Melek"}}, "extensions": {"cost": 1}}
        with patch.object(cards.urllib.request, "urlopen",
                          return_value=io.BytesIO(json.dumps(body).encode())):
            self.assertEqual(cards.graphql("query Test { user { name } }", {}),
                             body["data"])

    def test_graphql_serializes_query_and_variables(self):
        query, variables = "query($login: String!) { user(login: $login) { id } }", {"login": "Melek"}
        with patch.object(cards.urllib.request, "urlopen",
                          return_value=io.BytesIO(b'{"data": {}}')) as request:
            cards.graphql(query, variables)
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.github.com/graphql")
        self.assertEqual(json.loads(sent.data), {"query": query, "variables": variables})

    def test_graphql_request_has_a_timeout(self):
        with patch.object(cards.urllib.request, "urlopen",
                          return_value=io.BytesIO(b'{"data": {}}')) as request:
            cards.graphql("query { viewer { login } }", {})
        self.assertEqual(request.call_args.kwargs["timeout"], 30)

    def test_graphql_does_not_accept_partial_data_with_errors(self):
        body = {"data": {"user": None}, "errors": [{"message": "rate limited"}]}
        with patch.object(cards.urllib.request, "urlopen",
                          return_value=io.BytesIO(json.dumps(body).encode())):
            with self.assertRaisesRegex(RuntimeError, "rate limited"):
                cards.graphql("query { user { id } }", {})

    def test_history_requests_each_calendar_year_once(self):
        _, requests = self.history()
        years = [dt.datetime.fromisoformat(call.args[1]["from"]).year for call in requests]
        self.assertEqual(years, [2024, 2025, 2026])

    def test_first_history_request_starts_at_account_creation(self):
        _, requests = self.history()
        self.assertEqual(requests[0].args[1]["from"], "2024-06-15T09:30:00+00:00")
        self.assertEqual(requests[0].args[1]["to"], "2024-12-31T23:59:59+00:00")

    def test_current_year_request_ends_at_now(self):
        _, requests = self.history()
        self.assertEqual(requests[-1].args[1]["from"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(requests[-1].args[1]["to"], NOW.isoformat())

    def test_lifetime_commits_sum_all_years(self):
        (commits, _), _ = self.history()
        self.assertEqual(commits, 56)

    def test_history_excludes_padding_outside_each_requested_year(self):
        (_, days), _ = self.history()
        self.assertEqual(days, [
            day("2024-06-15", 2), day("2024-12-31", 3),
            day("2025-01-01", 5), day("2025-12-31", 6),
            day("2026-10-30", 20), day("2026-10-31", 20)])

    def test_aggregated_history_preserves_year_boundary_streak(self):
        (_, days), _ = self.history()
        self.assertEqual(cards.streak_metrics(days, NOW.date()),
                         {"current": 2, "longest": 2, "active_days": 6})

    def test_main_without_token_stops_before_network_or_output(self):
        with patch.object(cards, "TOKEN", None), patch.object(cards, "graphql") as request:
            with self.assertRaisesRegex(SystemExit, "Set GH_TOKEN or GITHUB_TOKEN"):
                cards.main()
        request.assert_not_called()

    def test_profile_repository_is_excluded_from_project_stats(self):
        def check(root, out):
            stats = json.loads((out / "activity-data.json").read_text())["stats"]
            self.assertEqual(stats["repos"], 2)
            self.assertEqual(stats["stars"], 4)
        self.generate(check)

    def test_ignored_languages_do_not_enter_the_card(self):
        def check(root, out):
            text = "".join(ET.fromstring((out / "top-langs.svg").read_text()).itertext())
            self.assertNotIn("Hack", text)
            self.assertNotIn("9999", text)
        self.generate(check)

    def test_language_percentages_use_combined_repository_sizes(self):
        def check(root, out):
            text = "".join(ET.fromstring((out / "top-langs.svg").read_text()).itertext())
            self.assertIn("Python 80.0%", text)
            self.assertIn("JavaScript 20.0%", text)
        self.generate(check)

