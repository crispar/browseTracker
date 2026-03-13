import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gui.ui_style import _pick_font_family


class UIFontSelectionTestCase(unittest.TestCase):
    def test_windows_prefers_korean_friendly_font(self):
        available = {'Segoe UI', 'Malgun Gothic', 'Arial'}
        self.assertEqual(_pick_font_family(available, 'Windows'), 'Malgun Gothic')

    def test_windows_falls_back_to_segoe_ui(self):
        available = {'Segoe UI', 'Arial'}
        self.assertEqual(_pick_font_family(available, 'Windows'), 'Segoe UI')

    def test_unknown_platform_uses_default_when_no_match(self):
        available = {'Courier New'}
        self.assertEqual(_pick_font_family(available, 'OtherOS'), 'TkDefaultFont')


if __name__ == '__main__':
    unittest.main()
