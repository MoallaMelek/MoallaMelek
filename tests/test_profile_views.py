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
