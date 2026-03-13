import copy
import sys
import unittest
from datetime import datetime
from pathlib import Path
import tkinter as tk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from database.models import Link, Category, Tag
from gui.detail_panel import DetailPanel


class FakeDBManager:
    def __init__(self):
        self.categories = [
            Category(id=1, name='Work', color='#111111'),
            Category(id=2, name='Study', color='#222222'),
        ]
        self.tags = {
            'alpha': Tag(id=1, name='alpha'),
            'beta': Tag(id=2, name='beta'),
        }
        self.links = {}

        self.update_link_calls = []
        self.remove_link_category_calls = []
        self.add_link_category_calls = []
        self.remove_tag_calls = []
        self.add_tag_calls = []
        self.delete_calls = []

    def seed_link(self):
        link = Link(
            id=101,
            url='https://example.com',
            title='Original Title',
            notes='Original note',
            access_count=3,
            is_favorite=False,
            created_at=datetime(2026, 1, 10, 9, 0, 0),
            last_accessed_at=datetime(2026, 1, 11, 10, 30, 0),
        )
        link.categories = [copy.deepcopy(self.categories[0])]
        link.tags = [copy.deepcopy(self.tags['alpha']), copy.deepcopy(self.tags['beta'])]
        self.links[link.id] = link
        return link.id

    def get_categories(self):
        return copy.deepcopy(self.categories)

    def get_link(self, link_id):
        link = self.links.get(link_id)
        return copy.deepcopy(link) if link else None

    def update_link(self, link_id, title=None, notes=None, is_favorite=False):
        self.update_link_calls.append({
            'link_id': link_id,
            'title': title,
            'notes': notes,
            'is_favorite': is_favorite,
        })
        link = self.links[link_id]
        link.title = title
        link.notes = notes
        link.is_favorite = is_favorite

    def remove_link_from_category(self, link_id, category_id):
        self.remove_link_category_calls.append((link_id, category_id))
        link = self.links[link_id]
        link.categories = [cat for cat in link.categories if cat.id != category_id]

    def add_link_to_category(self, link_id, category_id):
        self.add_link_category_calls.append((link_id, category_id))
        link = self.links[link_id]
        if category_id not in {cat.id for cat in link.categories}:
            category = next(cat for cat in self.categories if cat.id == category_id)
            link.categories.append(copy.deepcopy(category))

    def remove_tag_from_link(self, link_id, tag_id):
        self.remove_tag_calls.append((link_id, tag_id))
        link = self.links[link_id]
        link.tags = [tag for tag in link.tags if tag.id != tag_id]

    def add_tag_to_link(self, link_id, tag_name):
        self.add_tag_calls.append((link_id, tag_name))
        if tag_name not in self.tags:
            self.tags[tag_name] = Tag(id=max(tag.id for tag in self.tags.values()) + 1, name=tag_name)

        link = self.links[link_id]
        if tag_name not in {tag.name for tag in link.tags}:
            link.tags.append(copy.deepcopy(self.tags[tag_name]))

    def delete_link(self, link_id):
        self.delete_calls.append(link_id)
        return True


class DetailPanelTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk unavailable in this environment: {exc}')

        self.root.geometry('900x650')
        self.root.update_idletasks()

        self.db = FakeDBManager()
        self.link_id = self.db.seed_link()
        self.saved_events = []

        self.panel = DetailPanel(self.root, self.db, on_save=self.saved_events.append)
        self.panel.pack(fill=tk.BOTH, expand=True)

        self.panel.set_link(self.db.get_link(self.link_id))
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, 'root'):
            self.root.destroy()

    @staticmethod
    def _is_enabled(widget):
        return str(widget['state']) != 'disabled'

    def test_action_buttons_stay_visible_when_height_is_small(self):
        self.root.geometry('640x280')
        self.root.update_idletasks()

        panel_height = self.panel.winfo_height()
        button_bottom = self.panel.button_frame.winfo_y() + self.panel.button_frame.winfo_height()

        self.assertTrue(self.panel.save_button.winfo_ismapped())
        self.assertLessEqual(button_bottom, panel_height)

    def test_save_and_revert_state_tracks_dirty_changes(self):
        self.assertFalse(self._is_enabled(self.panel.save_button))
        self.assertFalse(self._is_enabled(self.panel.revert_button))

        self.panel.title_var.set('Changed title')
        self.root.update_idletasks()

        self.assertTrue(self._is_enabled(self.panel.save_button))
        self.assertTrue(self._is_enabled(self.panel.revert_button))

        self.panel._revert_changes()
        self.root.update_idletasks()

        self.assertEqual(self.panel.title_var.get(), 'Original Title')
        self.assertFalse(self._is_enabled(self.panel.save_button))
        self.assertFalse(self._is_enabled(self.panel.revert_button))

    def test_unsaved_helper_methods_for_navigation_guard(self):
        self.assertFalse(self.panel.has_unsaved_changes())

        self.panel.title_var.set('Draft title')
        self.root.update_idletasks()
        self.assertTrue(self.panel.has_unsaved_changes())

        self.assertTrue(self.panel.revert_current_changes())
        self.root.update_idletasks()
        self.assertFalse(self.panel.has_unsaved_changes())
        self.assertEqual(self.panel.title_var.get(), 'Original Title')

        self.panel.title_var.set('Saved by helper')
        self.root.update_idletasks()
        self.assertTrue(self.panel.save_current_changes())
        self.root.update_idletasks()
        self.assertFalse(self.panel.has_unsaved_changes())

    def test_save_updates_db_and_emits_callback(self):
        self.panel.title_var.set('New title')
        self.panel.favorite_var.set(True)
        self.panel.tags_var.set('alpha, gamma')
        self.panel.notes_text.delete('1.0', tk.END)
        self.panel.notes_text.insert('1.0', '한글 입력 안정성 확인 메모')

        category_ids = sorted(self.panel.category_vars.keys())
        self.panel.category_vars[category_ids[0]][0].set(False)
        self.panel.category_vars[category_ids[1]][0].set(True)

        self.root.update_idletasks()
        self.panel._save_changes()
        self.root.update_idletasks()

        self.assertEqual(len(self.db.update_link_calls), 1)
        call = self.db.update_link_calls[0]
        self.assertEqual(call['title'], 'New title')
        self.assertEqual(call['notes'], '한글 입력 안정성 확인 메모')
        self.assertTrue(call['is_favorite'])

        self.assertIn((self.link_id, 1), self.db.remove_link_category_calls)
        self.assertIn((self.link_id, 2), self.db.add_link_category_calls)
        self.assertIn((self.link_id, 2), self.db.remove_tag_calls)
        self.assertIn((self.link_id, 'gamma'), self.db.add_tag_calls)

        self.assertEqual(len(self.saved_events), 1)
        self.assertFalse(self._is_enabled(self.panel.save_button))


if __name__ == '__main__':
    unittest.main()
