import datetime as dt
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cards',Path(__file__).parents[1]/'scripts/generate_cards.py')
cards=importlib.util.module_from_spec(spec);spec.loader.exec_module(cards)

class StreakBoundaryTests(unittest.TestCase):
    def test_year_boundary_and_unfinished_today(self):
        days=[{'date':d,'contributionCount':1} for d in ['2025-12-30','2025-12-31','2026-01-01']]
        self.assertEqual(cards.streak_metrics(days,dt.date(2026,1,2)),{'current':3,'longest':3,'active_days':3})
        self.assertEqual(cards.streak_metrics(days,dt.date(2026,1,3))['current'],0)

    def test_inactive_gap_breaks_longest_streak_and_future_is_ignored(self):
        days=[{'date':d,'contributionCount':1} for d in ['2026-01-01','2026-01-03','2026-01-04','2026-01-06']]
        self.assertEqual(cards.streak_metrics(days,dt.date(2026,1,4)),{'current':2,'longest':2,'active_days':3})

    def test_calendar_duplicates_do_not_inflate_activity(self):
        days=[{'date':'2026-01-01','contributionCount':2}]*3
        self.assertEqual(len(cards.calendar_days(days,dt.date(2026,1,1))),1)
        self.assertEqual(cards.streak_metrics(days,dt.date(2026,1,1))['active_days'],1)
