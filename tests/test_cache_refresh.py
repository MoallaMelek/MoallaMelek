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

    def test_repeated_image_references_receive_the_same_version(self):
        result = self.refresh("assets/activity.svg?v=one\nassets/activity.svg?v=two")
        self.assertEqual(result.splitlines(),
                         [f"assets/activity.svg?v={self.digest('activity')}"] * 2)

    def test_unicode_alt_text_is_unchanged(self):
        result = self.refresh('<img width="100%" src="assets/activity.svg?v=old" alt="Activité — مُلخّص" />')
        self.assertIn('alt="Activité — مُلخّص"', result)
        self.assertIn('width="100%"', result)

    def test_unrelated_external_image_is_not_versioned(self):
        original = '<img src="https://example.com/chart.svg?v=keep" />'
        self.assertEqual(self.refresh(original), original)

    def test_nonimage_links_keep_their_versions(self):
        original = '<a href="https://example.com/?v=keep">Documentation</a>'
        self.assertEqual(self.refresh(original), original)

    def test_hyphenated_project_pin_is_versioned(self):
        result = self.refresh('<img src="assets/pin-Reward-Goblin.svg?v=old" />',
                              {"pin-Reward-Goblin.svg": "project pin"})
        self.assertIn(f'pin-Reward-Goblin.svg?v={self.digest("project pin")}', result)

    def test_external_streak_cache_tracks_streak_contents(self):
        source = '<img src="https://streak-stats.demolab.com?user=Melek&v=old" />'
        self.assertNotEqual(self.refresh(source),
                            self.refresh(source, {"streak.svg": "new streak"}))

