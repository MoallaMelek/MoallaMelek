

import datetime as dt
import importlib.util
import unittest
import tempfile
from unittest.mock import patch
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

    def test_card_content_is_visible_without_animation_and_respects_reduced_motion(self):
        svg=cards.frame(100,50,'<text class="fade">Visible</text>')
        self.assertIn('.fade { opacity: 1;',svg)
        self.assertIn('prefers-reduced-motion: reduce',svg)
        self.assertIn('animation: none;',svg)

    def test_external_streak_cache_changes_when_contributions_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);assets=root/'assets';assets.mkdir()
            (assets/'streak.svg').write_text('unchanged streak length',encoding='utf-8')
            (assets/'stats.svg').write_text('20 contributions',encoding='utf-8')
            (root/'README.md').write_text('<img src="https://streak-stats.demolab.com?user=MoallaMelek&v=old" />',encoding='utf-8')
            with patch.object(cards,'OUT',assets):
                cards.refresh_card_links()
                first=(root/'README.md').read_text(encoding='utf-8')
                (assets/'stats.svg').write_text('21 contributions',encoding='utf-8')
                cards.refresh_card_links()
                self.assertNotEqual(first,(root/'README.md').read_text(encoding='utf-8'))

    def test_empty_calendar_remains_a_valid_svg(self):
        ET.fromstring(cards.heatmap_card([],dt.date(2026,10,21)))

if __name__=='__main__':unittest.main()
