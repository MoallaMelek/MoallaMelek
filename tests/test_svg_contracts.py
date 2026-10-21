import datetime as dt
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cards',Path(__file__).parents[1]/'scripts/generate_cards.py')
cards=importlib.util.module_from_spec(spec);spec.loader.exec_module(cards)
import xml.etree.ElementTree as ET

class SvgContractTests(unittest.TestCase):
    def test_frame_escapes_dynamic_titles(self):
        root=ET.fromstring(cards.frame(900,280,'',title='A & B <test>'))
        self.assertEqual(root.attrib['viewBox'],'0 0 900 280')
        self.assertEqual(root.find('{http://www.w3.org/2000/svg}text').text,'A & B <test>')

    def test_calendar_preserves_existing_dimensions_and_green_palette(self):
        svg=cards.heatmap_card([{'date':'2026-10-21','contributionCount':10}],dt.date(2026,10,21))
        root=ET.fromstring(svg)
        self.assertEqual((root.attrib['width'],root.attrib['height']),('900','180'))
        self.assertIn('#39D353',svg)
        self.assertIn('prefers-reduced-motion',svg)

    def test_activity_curve_preserves_geometry_and_does_not_emit_nonfinite_points(self):
        svg=cards.activity_card([{'date':'2026-10-20','contributionCount':0}])
        root=ET.fromstring(svg)
        self.assertEqual((root.attrib['width'],root.attrib['height']),('900','280'))
        self.assertNotIn('nan',svg.lower())
        self.assertNotIn('inf,',svg.lower())
