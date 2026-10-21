

import datetime as dt
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

spec=importlib.util.spec_from_file_location('cards',Path(__file__).parents[1]/'scripts/generate_cards.py')
cards=importlib.util.module_from_spec(spec);spec.loader.exec_module(cards)
NS={'s':'http://www.w3.org/2000/svg'}

class CardTests(unittest.TestCase):
    def test_heatmap_has_each_day_once_and_excludes_future_padding(self):
        today=dt.date(2026,10,21)
        svg=cards.heatmap_card([{'date':'2026-10-21','contributionCount':7},
                                {'date':'2026-10-22','contributionCount':100}],today)
        root=ET.fromstring(svg)
        dates=[r.get('data-date') for r in root.findall('s:rect',NS) if r.get('data-date')]
        self.assertEqual(len(dates),365)
        self.assertEqual(len(set(dates)),365)
        self.assertEqual(dates[-1],'2026-10-21')
        self.assertIn('2026-10-21: 7 contributions',svg)
        self.assertNotIn('2026-10-22',svg)

    def test_calendar_and_curve_share_source_counts(self):
        days=[{'date':'2026-10-20','contributionCount':3}]
        self.assertIn('2026-10-20: 3 contributions',cards.heatmap_card(days,dt.date(2026,10,21)))
        self.assertIn('3 contributions since Sep 26, 2026',cards.activity_card(days))

    def test_empty_calendar_remains_a_valid_svg(self):
        ET.fromstring(cards.heatmap_card([],dt.date(2026,10,21)))

if __name__=='__main__':unittest.main()
