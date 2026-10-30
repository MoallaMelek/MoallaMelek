"""Regression coverage for calendar data and unchanged activity-card rendering."""

import datetime as dt
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "activity_cards", Path(__file__).parents[1] / "scripts" / "generate_cards.py"
)
cards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cards)
NS = {"s": "http://www.w3.org/2000/svg"}


class ActivityRegressionTests(unittest.TestCase):

    def test_leap_day_keeps_a_continuous_streak(self):
        days = [{"date": date, "contributionCount": 1}
                for date in ("2024-02-28", "2024-02-29", "2024-03-01")]
        self.assertEqual(cards.streak_metrics(days, dt.date(2024, 3, 1)),
                         {"current": 3, "longest": 3, "active_days": 3})

    def test_unordered_calendar_does_not_break_a_streak(self):
        days = [{"date": date, "contributionCount": 2}
                for date in ("2026-10-30", "2026-10-28", "2026-10-29")]
        result = cards.streak_metrics(days, dt.date(2026, 10, 30))
        self.assertEqual(result["current"], 3)
        self.assertEqual(result["longest"], 3)

    def test_zero_contributions_are_not_active_days(self):
        days = [{"date": "2026-10-29", "contributionCount": 0},
                {"date": "2026-10-30", "contributionCount": 20}]
        self.assertEqual(cards.streak_metrics(days, dt.date(2026, 10, 30)),
                         {"current": 1, "longest": 1, "active_days": 1})

    def test_future_only_calendar_has_no_streak(self):
        days = [{"date": "2026-10-31", "contributionCount": 20}]
        self.assertEqual(cards.streak_metrics(days, dt.date(2026, 10, 30)),
                         {"current": 0, "longest": 0, "active_days": 0})

    def test_empty_history_has_zero_metrics(self):
        self.assertEqual(cards.streak_metrics([], dt.date(2026, 10, 30)),
                         {"current": 0, "longest": 0, "active_days": 0})

    def test_zero_activity_curve_stays_on_baseline(self):
        days = [{"date": "2026-09-26", "contributionCount": 0},
                {"date": "2026-09-27", "contributionCount": 0}]
        root = ET.fromstring(cards.activity_card(days))
        points = root.find("s:polyline", NS).get("points").split()
        self.assertEqual(points, ["50.0,235.0", "875.0,235.0"])
        self.assertIn("0 contributions", "".join(root.itertext()))

    def test_large_contribution_peak_stays_inside_chart(self):
        days = [{"date": "2026-09-26", "contributionCount": 1001},
                {"date": "2026-09-27", "contributionCount": 0}]
        root = ET.fromstring(cards.activity_card(days))
        points = [tuple(map(float, point.split(","))) for point
                  in root.find("s:polyline", NS).get("points").split()]
        self.assertTrue(all(50 <= x <= 875 and 55 <= y <= 235 for x, y in points))
        self.assertIn("1001 contributions", "".join(root.itertext()))
