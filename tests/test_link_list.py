import sys
import unittest
from pathlib import Path
import tkinter as tk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from database.models import Link
from gui.link_list import LinkListView


class LinkListViewTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk unavailable in this environment: {exc}')

        self.root.geometry('900x500')
        self.view = LinkListView(self.root)
        self.view.pack(fill=tk.BOTH, expand=True)

        links = [
            Link(id=1, url='https://a.example.com', title='A'),
            Link(id=2, url='https://b.example.com', title='B'),
        ]
        self.view.set_links(links)
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, 'root'):
            self.root.destroy()

    def test_select_link_by_id_selects_expected_item(self):
        selected = self.view.select_link_by_id(2)
        self.assertTrue(selected)

        selected_links = self.view.get_selected_links()
        self.assertEqual(len(selected_links), 1)
        self.assertEqual(selected_links[0].id, 2)


if __name__ == '__main__':
    unittest.main()
