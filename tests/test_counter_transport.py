"""Transport and malformed-response recovery for the profile-view snapshot."""

import importlib.util
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

SPEC = importlib.util.spec_from_file_location(
    "transport_views", Path(__file__).parents[1] / "scripts" / "refresh_profile_views.py")
views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(views)


class CounterTransportTests(unittest.TestCase):
    def assert_keeps_snapshot(self, body):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "views.svg"
            original = views.render_badge(70)
            out.write_text(original, encoding="utf-8")
            response = MagicMock()
            response.__enter__.return_value.read.return_value = body
            with patch.object(views.urllib.request, "urlopen", return_value=response):
                self.assertFalse(views.refresh(out))
            self.assertEqual(out.read_text(encoding="utf-8"), original)

    def valid_response(self, count=70):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = views.render_badge(count).encode()
        return response


    def test_oversized_response_does_not_replace_snapshot(self):
        self.assert_keeps_snapshot(b"x" * 32769)

    def test_truncated_svg_does_not_replace_snapshot(self):
        self.assert_keeps_snapshot(b'<svg xmlns="http://www.w3.org/2000/svg"><title>')

    def test_empty_counter_title_does_not_replace_snapshot(self):
        self.assert_keeps_snapshot(b'<svg xmlns="http://www.w3.org/2000/svg"><title/></svg>')

