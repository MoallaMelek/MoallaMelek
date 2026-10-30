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

    def test_large_count_renders_without_losing_digits(self):
        count = 123456789
        self.assertEqual(views.read_count(views.render_badge(count)), count)

    def test_network_failure_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "views.svg"
            before = views.render_badge(42)
            out.write_text(before, encoding="utf-8")
            with patch.object(views.urllib.request, "urlopen",
                              side_effect=urllib.error.URLError("offline")):
                self.assertFalse(views.refresh(out))
            self.assertEqual(out.read_text(encoding="utf-8"), before)

    def test_lower_counter_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "views.svg"
            before = views.render_badge(42)
            out.write_text(before, encoding="utf-8")
            response = MagicMock()
            response.__enter__.return_value.read.return_value = views.render_badge(41).encode()
            with patch.object(views.urllib.request, "urlopen", return_value=response):
                self.assertFalse(views.refresh(out))
            self.assertEqual(out.read_text(encoding="utf-8"), before)

    def test_first_refresh_failure_does_not_create_a_badge(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "views.svg"
            with patch.object(views.urllib.request, "urlopen",
                              side_effect=urllib.error.URLError("offline")):
                with self.assertRaises(urllib.error.URLError):
                    views.refresh(out)
            self.assertFalse(out.exists())
