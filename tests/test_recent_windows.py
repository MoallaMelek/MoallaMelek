"""Date-window regression coverage for the recent-activity card."""

import datetime as dt
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "window_cards", Path(__file__).parents[1] / "scripts" / "generate_cards.py")
cards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cards)
NS = {"s": "http://www.w3.org/2000/svg"}


class RecentWindowTests(unittest.TestCase):
    def assert_window(self, entries, expected, active, now=None):
        now = now or dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)

        class FrozenDatetime(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return now.astimezone(tz) if tz else now.replace(tzinfo=None)

        clock = SimpleNamespace(datetime=FrozenDatetime, date=dt.date,
                                timezone=dt.timezone, timedelta=dt.timedelta)
        days = [{"date": (now.date() - dt.timedelta(days=offset)).isoformat(),
                 "contributionCount": count} for offset, count in entries]
        with patch.object(cards, "dt", clock):
            root = ET.fromstring(cards.recent_activity_card(days))
        values = [int(node.text.replace(",", "")) for node in root.findall("s:text", NS)
                  if node.get("y") == "84"]
        self.assertEqual(values, expected)
        self.assertIn(f"{active} active days in the last 31 days", "".join(root.itertext()))


    def test_today_is_in_all_windows(self):
        self.assert_window([(0, 30)], [30, 30, 30], 1)

    def test_six_days_ago_is_in_week(self):
        self.assert_window([(6, 7)], [0, 7, 7], 1)

    def test_seven_days_ago_is_outside_week(self):
        self.assert_window([(7, 9)], [0, 0, 9], 1)

    def test_thirty_days_ago_is_in_month(self):
        self.assert_window([(30, 11)], [0, 0, 11], 1)

    def test_thirty_one_days_ago_is_outside_month(self):
        self.assert_window([(31, 13)], [0, 0, 0], 0)

