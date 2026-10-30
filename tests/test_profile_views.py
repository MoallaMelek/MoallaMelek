"""Profile-view parsing and last-good-snapshot recovery regressions."""

import importlib.util
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

SPEC = importlib.util.spec_from_file_location(
    "profile_views", Path(__file__).parents[1] / "scripts" / "refresh_profile_views.py"
)
views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(views)


class ProfileViewRegressionTests(unittest.TestCase):

    def test_numeric_svg_badge_is_read(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><title>PROFILE VIEWS: 1234</title></svg>'
        self.assertEqual(views.read_count(svg), 1234)

    def test_zero_views_is_a_valid_count(self):
        self.assertEqual(views.read_count(views.render_badge(0)), 0)

    def test_html_error_page_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expected an SVG"):
            views.read_count("<html><title>PROFILE VIEWS: 20</title></html>")

    def test_missing_title_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "numeric view count"):
            views.read_count('<svg xmlns="http://www.w3.org/2000/svg"/>')

    def test_unavailable_counter_is_rejected(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><title>PROFILE VIEWS: unavailable</title></svg>'
        with self.assertRaisesRegex(ValueError, "numeric view count"):
            views.read_count(svg)
