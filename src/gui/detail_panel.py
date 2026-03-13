"""Detail panel for viewing and editing link information."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import webbrowser

from database.models import Link
from database.db_manager import DatabaseManager
from gui.ui_style import get_body_font


class DetailPanel(ttk.Frame):
    """Panel for displaying and editing link details."""

    def __init__(self, parent, db_manager: DatabaseManager,
                 on_save: Optional[Callable] = None):
        """Initialize the detail panel."""
        super().__init__(parent)

        self.db_manager = db_manager
        self.on_save = on_save
        self.current_link = None

        self._is_dirty = False
        self._suspend_change_tracking = False
        self.category_vars = {}
        self.body_font = get_body_font(self.winfo_toplevel(), size=10)

        self._build_ui()
        self._bind_change_tracking()
        self.clear()

    def _build_ui(self):
        """Build UI with scrollable content and fixed action bar."""
        container = ttk.Frame(self, padding=(10, 10, 10, 0))
        container.pack(fill=tk.BOTH, expand=True)

        # Scrollable form area
        scroll_host = ttk.Frame(container)
        scroll_host.pack(fill=tk.BOTH, expand=True)

        self.content_canvas = tk.Canvas(
            scroll_host,
            highlightthickness=0,
            borderwidth=0
        )
        self.content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content_scrollbar = ttk.Scrollbar(
            scroll_host,
            orient=tk.VERTICAL,
            command=self.content_canvas.yview
        )
        self.content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)

        self.content_frame = ttk.Frame(self.content_canvas)
        self.content_window_id = self.content_canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor=tk.NW
        )

        self.content_frame.bind('<Configure>', self._on_content_configure)
        self.content_canvas.bind('<Configure>', self._on_canvas_configure)
        self.content_canvas.bind('<MouseWheel>', self._on_canvas_mousewheel)
        self.content_frame.bind('<MouseWheel>', self._on_canvas_mousewheel)

        # Title section
        title_frame = ttk.LabelFrame(self.content_frame, text="Title", padding=6)
        title_frame.pack(fill=tk.X, pady=(0, 6))

        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(title_frame, textvariable=self.title_var)
        self.title_entry.pack(fill=tk.X)

        # URL section
        url_frame = ttk.LabelFrame(self.content_frame, text="URL", padding=6)
        url_frame.pack(fill=tk.X, pady=(0, 6))

        url_inner = ttk.Frame(url_frame)
        url_inner.pack(fill=tk.X)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_inner, textvariable=self.url_var, state='readonly')
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.open_button = ttk.Button(
            url_inner,
            text="Open",
            width=7,
            command=self._open_url
        )
        self.open_button.pack(side=tk.LEFT, padx=(6, 0))

        # Categories section
        cat_frame = ttk.LabelFrame(self.content_frame, text="Categories", padding=6)
        cat_frame.pack(fill=tk.X, pady=(0, 6))

        self.category_frame = ttk.Frame(cat_frame)
        self.category_frame.pack(fill=tk.X)

        # Tags section
        tag_frame = ttk.LabelFrame(self.content_frame, text="Tags", padding=6)
        tag_frame.pack(fill=tk.X, pady=(0, 6))

        self.tags_var = tk.StringVar()
        self.tags_entry = ttk.Entry(tag_frame, textvariable=self.tags_var)
        self.tags_entry.pack(fill=tk.X)
        ttk.Label(tag_frame, text="Separate tags with commas").pack(anchor=tk.W, pady=(4, 0))

        # Notes section
        notes_frame = ttk.LabelFrame(self.content_frame, text="Notes", padding=6)
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        text_frame = ttk.Frame(notes_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        notes_scrollbar = ttk.Scrollbar(text_frame)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.notes_text = tk.Text(
            text_frame,
            height=8,
            wrap=tk.WORD,
            undo=True,
            autoseparators=True,
            maxundo=200,
            font=self.body_font,
            yscrollcommand=notes_scrollbar.set
        )
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scrollbar.config(command=self.notes_text.yview)
        self.notes_text.bind('<<Modified>>', self._on_notes_modified)

        # Statistics section
        stats_frame = ttk.LabelFrame(self.content_frame, text="Statistics", padding=6)
        stats_frame.pack(fill=tk.X, pady=(0, 6))

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)

        ttk.Label(stats_grid, text="Access Count:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.access_count_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.access_count_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(stats_grid, text="Last Accessed:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.last_accessed_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.last_accessed_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(stats_grid, text="Created:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.created_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.created_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        self.favorite_var = tk.BooleanVar()
        self.favorite_check = ttk.Checkbutton(
            stats_grid,
            text="Favorite",
            variable=self.favorite_var
        )
        self.favorite_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Fixed action bar (always visible)
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=(6, 6))

        self.button_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        self.button_frame.pack(fill=tk.X)

        left_actions = ttk.Frame(self.button_frame)
        left_actions.pack(side=tk.LEFT)

        self.save_button = ttk.Button(
            left_actions,
            text="Save",
            width=10,
            command=self._save_changes
        )
        self.save_button.pack(side=tk.LEFT, padx=(0, 6))

        self.revert_button = ttk.Button(
            left_actions,
            text="Revert",
            width=10,
            command=self._revert_changes
        )
        self.revert_button.pack(side=tk.LEFT)

        self.change_hint_var = tk.StringVar(value="")
        self.change_hint = ttk.Label(self.button_frame, textvariable=self.change_hint_var)
        self.change_hint.pack(side=tk.RIGHT, padx=(0, 10))

        self.delete_button = ttk.Button(
            self.button_frame,
            text="Delete",
            width=10,
            command=self._delete_link
        )
        self.delete_button.pack(side=tk.RIGHT)

        for widget in (self.title_entry, self.tags_entry, self.notes_text):
            widget.bind('<Control-s>', self._on_shortcut_save)
            widget.bind('<Escape>', self._on_shortcut_revert)

    def _bind_change_tracking(self):
        """Track form changes to control Save/Revert state."""
        self.title_var.trace_add('write', self._mark_dirty)
        self.tags_var.trace_add('write', self._mark_dirty)
        self.favorite_var.trace_add('write', self._mark_dirty)

    def _on_content_configure(self, _event=None):
        """Update canvas scrollregion whenever content size changes."""
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox('all'))

    def _on_canvas_configure(self, event=None):
        """Keep content frame width in sync with canvas width."""
        if event:
            self.content_canvas.itemconfigure(self.content_window_id, width=event.width)

    def _on_canvas_mousewheel(self, event):
        """Scroll form area with mouse wheel when content overflows."""
        if self.content_frame.winfo_reqheight() > self.content_canvas.winfo_height():
            self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_shortcut_save(self, _event=None):
        """Handle Ctrl+S."""
        self._save_changes()
        return 'break'

    def has_unsaved_changes(self):
        """Return whether the current form has unsaved edits."""
        return bool(self.current_link and self._is_dirty)

    def save_current_changes(self):
        """Public wrapper for save with success result."""
        return self._save_changes()

    def revert_current_changes(self):
        """Public wrapper for revert with success result."""
        return self._revert_changes()

    def _on_shortcut_revert(self, _event=None):
        """Handle Escape."""
        self._revert_changes()
        return 'break'

    def _on_notes_modified(self, _event=None):
        """Mark notes as dirty while avoiding false positives during programmatic updates."""
        if self._suspend_change_tracking:
            self.notes_text.edit_modified(False)
            return

        if self.notes_text.edit_modified():
            self._mark_dirty()
            self.notes_text.edit_modified(False)

    def _mark_dirty(self, *_args):
        """Mark form as dirty if a link is selected and user changed something."""
        if self._suspend_change_tracking or not self.current_link:
            return
        self._is_dirty = True
        self._update_action_state()

    def _mark_clean(self):
        """Clear dirty flag and update actions."""
        self._is_dirty = False
        self.change_hint_var.set("")
        self.notes_text.edit_modified(False)
        self._update_action_state()

    def _update_action_state(self):
        """Enable/disable action buttons based on current state."""
        has_link = self.current_link is not None
        can_save = has_link and self._is_dirty

        self.save_button.config(state='normal' if can_save else 'disabled')
        self.revert_button.config(state='normal' if can_save else 'disabled')
        self.delete_button.config(state='normal' if has_link else 'disabled')
        self.open_button.config(state='normal' if has_link else 'disabled')

        if has_link and self._is_dirty:
            self.change_hint_var.set("Unsaved changes")
        elif has_link:
            self.change_hint_var.set("All changes saved")
        else:
            self.change_hint_var.set("")

    def set_link(self, link: Optional[Link]):
        """Set the link to display/edit."""
        self.current_link = link
        if not link:
            self.clear()
            return

        self._suspend_change_tracking = True
        try:
            self._set_enabled(True)

            self.title_var.set(link.title or '')
            self.url_var.set(link.url)
            self.favorite_var.set(link.is_favorite)

            tag_names = [tag.name for tag in link.tags]
            self.tags_var.set(', '.join(tag_names))

            self.notes_text.delete('1.0', tk.END)
            if link.notes:
                self.notes_text.insert('1.0', link.notes)

            self.access_count_var.set(str(link.access_count))

            if link.last_accessed_at:
                self.last_accessed_var.set(link.last_accessed_at.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                self.last_accessed_var.set('Never')

            if link.created_at:
                self.created_var.set(link.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                self.created_var.set('Unknown')

            self._update_categories()
            self.content_canvas.yview_moveto(0)
        finally:
            self._suspend_change_tracking = False

        self._mark_clean()

    def clear(self):
        """Clear the detail panel."""
        self.current_link = None
        self._suspend_change_tracking = True
        try:
            self._set_enabled(False)

            self.title_var.set('')
            self.url_var.set('')
            self.tags_var.set('')
            self.notes_text.delete('1.0', tk.END)
            self.access_count_var.set('--')
            self.last_accessed_var.set('--')
            self.created_var.set('--')
            self.favorite_var.set(False)

            for widget in self.category_frame.winfo_children():
                widget.destroy()
            self.category_vars = {}
        finally:
            self._suspend_change_tracking = False

        self._mark_clean()

    def _set_enabled(self, enabled: bool):
        """Enable or disable editable fields."""
        state = 'normal' if enabled else 'disabled'

        self.title_entry.config(state=state)
        self.tags_entry.config(state=state)
        self.notes_text.config(state=state)
        self.favorite_check.config(state=state)

        for widget in self.category_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                widget.config(state=state)

        self._update_action_state()

    def _update_categories(self):
        """Update category checkboxes."""
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        self.category_vars = {}

        all_categories = self.db_manager.get_categories()
        if not all_categories:
            ttk.Label(self.category_frame, text="No categories defined").pack(anchor=tk.W)
            return

        link_category_ids = set()
        if self.current_link:
            link_category_ids = {cat.id for cat in self.current_link.categories}

        row = 0
        col = 0
        max_cols = 2

        for category in all_categories:
            var = tk.BooleanVar(value=category.id in link_category_ids)
            var.trace_add('write', self._mark_dirty)
            self.category_vars[category.id] = (var, category)

            checkbox = ttk.Checkbutton(
                self.category_frame,
                text=category.name,
                variable=var
            )
            checkbox.grid(row=row, column=col, sticky=tk.W, padx=(0, 10), pady=2)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _save_changes(self):
        """Save changes to the database."""
        if not self.current_link or not self._is_dirty:
            return True

        try:
            self.current_link.title = self.title_var.get().strip()
            self.current_link.is_favorite = self.favorite_var.get()

            notes = self.notes_text.get('1.0', tk.END).strip()
            self.current_link.notes = notes if notes else None

            self.db_manager.update_link(
                link_id=self.current_link.id,
                title=self.current_link.title,
                notes=self.current_link.notes,
                is_favorite=self.current_link.is_favorite
            )

            for category in self.current_link.categories:
                self.db_manager.remove_link_from_category(
                    self.current_link.id,
                    category.id
                )

            for cat_id, (var, _category) in self.category_vars.items():
                if var.get():
                    self.db_manager.add_link_to_category(
                        self.current_link.id,
                        cat_id
                    )

            tag_text = self.tags_var.get().strip()
            new_tags = set()
            if tag_text:
                new_tags = {tag.strip() for tag in tag_text.split(',') if tag.strip()}

            current_tags = {tag.name for tag in self.current_link.tags}
            for tag in self.current_link.tags:
                if tag.name not in new_tags:
                    self.db_manager.remove_tag_from_link(
                        self.current_link.id,
                        tag.id
                    )

            for tag_name in new_tags:
                if tag_name not in current_tags:
                    self.db_manager.add_tag_to_link(
                        self.current_link.id,
                        tag_name
                    )

            refreshed = self.db_manager.get_link(self.current_link.id)
            if refreshed:
                self.set_link(refreshed)
            else:
                self._mark_clean()

            if self.on_save:
                self.on_save(refreshed or self.current_link)

            return True

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save changes: {e}")
            return False

    def _revert_changes(self):
        """Revert changes to original values from DB."""
        if not self.current_link:
            return False

        link = self.db_manager.get_link(self.current_link.id)
        if link:
            self.set_link(link)
            return True
        return False

    def _delete_link(self):
        """Move current link to Recycle Bin."""
        if not self.current_link:
            return

        msg = (
            f"Move this link to Recycle Bin?\n\n{self.current_link.title}\n\n"
            "You can restore it later from Edit -> Recycle Bin"
        )
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        try:
            if self.db_manager.delete_link(self.current_link.id):
                self.clear()
                if self.on_save:
                    self.on_save(None)
            else:
                messagebox.showerror("Delete Error", "Failed to move link to Recycle Bin")

        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to move link to Recycle Bin: {e}")

    def _open_url(self):
        """Open current URL in default browser."""
        if self.current_link:
            webbrowser.open(self.current_link.url)
