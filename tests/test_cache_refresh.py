"""Cache-version regressions that protect the existing README markup."""

import datetime as dt
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "cache_cards", Path(__file__).parents[1] / "scripts" / "generate_cards.py")
cards = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cards)


class CacheRefreshTests(unittest.TestCase):
    def refresh(self, readme, files=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "assets"
            out.mkdir()
            assets = {"stats.svg": "stats", "streak.svg": "streak",
                      "activity.svg": "activity"}
            assets.update(files or {})
            for name, content in assets.items():
                (out / name).write_text(content, encoding="utf-8")
            path = root / "README.md"
            path.write_text(readme, encoding="utf-8")
            with patch.object(cards, "OUT", out):
                cards.refresh_card_links()
            return path.read_text(encoding="utf-8")

    def digest(self, text):
        return hashlib.sha256(text.encode()).hexdigest()[:12]


    def test_unversioned_activity_image_gets_a_hash(self):
        result = self.refresh('<img src="assets/activity.svg" />')
        self.assertEqual(result, f'<img src="assets/activity.svg?v={self.digest("activity")}" />')

    def test_old_cache_version_is_replaced(self):
        result = self.refresh('<img src="assets/activity.svg?v=legacy_1" />')
        self.assertIn(f'activity.svg?v={self.digest("activity")}', result)
        self.assertNotIn("legacy_1", result)

