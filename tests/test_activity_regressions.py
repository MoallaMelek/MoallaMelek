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
