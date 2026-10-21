import datetime as dt
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cards',Path(__file__).parents[1]/'scripts/generate_cards.py')
cards=importlib.util.module_from_spec(spec);spec.loader.exec_module(cards)
import tempfile
from unittest.mock import patch

class ImageCacheIdentityTests(unittest.TestCase):
    def test_only_changed_image_hashes_change_and_readme_layout_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);assets=root/'assets';assets.mkdir()
            for name in ('stats','streak','heatmap','activity'):
                (assets/f'{name}.svg').write_text(name,encoding='utf-8')
            readme=root/'README.md'
            readme.write_text('before\n<img width="900" src="assets/heatmap.svg?v=old"/>\n<img src="assets/activity.svg?v=old"/>\nafter',encoding='utf-8')
            with patch.object(cards,'OUT',assets):
                cards.refresh_card_links();first=readme.read_text(encoding='utf-8')
                cards.refresh_card_links();self.assertEqual(readme.read_text(encoding='utf-8'),first)
                (assets/'heatmap.svg').write_text('new calendar data',encoding='utf-8')
                cards.refresh_card_links();second=readme.read_text(encoding='utf-8')
            self.assertNotEqual(first.splitlines()[1],second.splitlines()[1])
            self.assertEqual(first.splitlines()[2],second.splitlines()[2])
            self.assertTrue(second.startswith('before\n<img width="900"'))
            self.assertTrue(second.endswith('after'))
