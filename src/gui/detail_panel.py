"""
Detail panel for viewing and editing link information.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import webbrowser

from database.models import Link
from database.db_manager import DatabaseManager


class DetailPanel(ttk.Frame):
    """Panel for displaying and editing link details."""

    def __init__(self, parent, db_manager: DatabaseManager,
                 on_save: Optional[Callable] = None):
        """Initialize the detail panel.

        Args:
            parent: Parent widget
            db_manager: Database manager instance
            on_save: Callback when changes are saved
        """
        super().__init__(parent)

        self.db_manager = db_manager
        self.on_save = on_save
        self.current_link = None

        self._build_ui()
        self.clear()

    def _build_ui(self):
        """Build the UI components."""
        # Main container with padding
        container = ttk.Frame(self, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Title section
        title_frame = ttk.LabelFrame(container, text="Title", padding="5")
        title_frame.pack(fill=tk.X, pady=(0, 5))

        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(title_frame, textvariable=self.title_var)
        self.title_entry.pack(fill=tk.X)

        # URL section
        url_frame = ttk.LabelFrame(container, text="URL", padding="5")
        url_frame.pack(fill=tk.X, pady=(0, 5))

        url_inner = ttk.Frame(url_frame)
        url_inner.pack(fill=tk.X)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_inner, textvariable=self.url_var, state='readonly')
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(
            url_inner,
            text="🔗",
            width=3,
            command=self._open_url
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Categories section
        cat_frame = ttk.LabelFrame(container, text="Categories", padding="5")
        cat_frame.pack(fill=tk.X, pady=(0, 5))

        # Category checkboxes will be added dynamically
        self.category_frame = ttk.Frame(cat_frame)
        self.category_frame.pack(fill=tk.X)
        self.category_vars = {}

        # Tags section
        tag_frame = ttk.LabelFrame(container, text="Tags", padding="5")
        tag_frame.pack(fill=tk.X, pady=(0, 5))

        self.tags_var = tk.StringVar()
        self.tags_entry = ttk.Entry(tag_frame, textvariable=self.tags_var)
        self.tags_entry.pack(fill=tk.X)
        ttk.Label(tag_frame, text="Separate tags with commas", font=('', 8)).pack()

        # Notes section
        notes_frame = ttk.LabelFrame(container, text="Notes", padding="5")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Text widget with scrollbar
        text_frame = ttk.Frame(notes_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.notes_text = tk.Text(
            text_frame,
            height=6,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set
        )
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.notes_text.yview)

        # Statistics section
        stats_frame = ttk.LabelFrame(container, text="Statistics", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 5))

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)

        # Access count
        ttk.Label(stats_grid, text="Access Count:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.access_count_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.access_count_var).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # Last accessed
        ttk.Label(stats_grid, text="Last Accessed:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.last_accessed_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.last_accessed_var).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # Created
        ttk.Label(stats_grid, text="Created:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.created_var = tk.StringVar()
        ttk.Label(stats_grid, textvariable=self.created_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # Favorite checkbox
        self.favorite_var = tk.BooleanVar()
        self.favorite_check = ttk.Checkbutton(
            stats_grid,
            text="❤ Favorite",
            variable=self.favorite_var
        )
        self.favorite_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        # Button frame
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Save",
            command=self._save_changes
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Revert",
            command=self._revert_changes
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Delete",
            command=self._delete_link
        ).pack(side=tk.RIGHT)

    def set_link(self, link: Optional[Link]):
        """Set the link to display/edit.

        Args:
            link: Link object or None to clear
        """
        self.current_link = link

        if link:
            # Enable all fields
            self._set_enabled(True)

            # Set values
            self.title_var.set(link.title or '')
            self.url_var.set(link.url)
            self.favorite_var.set(link.is_favorite)

            # Set tags
            tag_names = [tag.name for tag in link.tags]
            self.tags_var.set(', '.join(tag_names))

            # Set notes
            self.notes_text.delete('1.0', tk.END)
            if link.notes:
                self.notes_text.insert('1.0', link.notes)

            # Set statistics
            self.access_count_var.set(str(link.access_count))

            if link.last_accessed_at:
                self.last_accessed_var.set(link.last_accessed_at.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                self.last_accessed_var.set('Never')

            if link.created_at:
                self.created_var.set(link.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                self.created_var.set('Unknown')

            # Update categories
            self._update_categories()

        else:
            self.clear()

    def clear(self):
        """Clear the detail panel."""
        self.current_link = None
        self._set_enabled(False)

        # Clear all fields
        self.title_var.set('')
        self.url_var.set('')
        self.tags_var.set('')
        self.notes_text.delete('1.0', tk.END)
        self.access_count_var.set('--')
        self.last_accessed_var.set('--')
        self.created_var.set('--')
        self.favorite_var.set(False)

        # Clear categories
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        self.category_vars = {}

    def _set_enabled(self, enabled: bool):
        """Enable or disable all input fields.

        Args:
            enabled: True to enable, False to disable
        """
        state = 'normal' if enabled else 'disabled'

        self.title_entry.config(state=state)
        self.tags_entry.config(state=state)
        self.notes_text.config(state=state)
        self.favorite_check.config(state=state)

    def _update_categories(self):
        """Update category checkboxes."""
        # Clear existing checkboxes
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        self.category_vars = {}

        # Get all categories
        all_categories = self.db_manager.get_categories()

        if not all_categories:
            ttk.Label(
                self.category_frame,
                text="No categories defined",
                foreground='gray'
            ).pack()
            return

        # Get link's categories
        link_categories = set()
        if self.current_link:
            link_categories = {cat.id for cat in self.current_link.categories}

        # Create checkboxes in a grid
        row = 0
        col = 0
        max_cols = 2

        for category in all_categories:
            var = tk.BooleanVar(value=category.id in link_categories)
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
        if not self.current_link:
            return

        try:
            # Update link properties
            self.current_link.title = self.title_var.get().strip()
            self.current_link.is_favorite = self.favorite_var.get()

            # Update notes
            notes = self.notes_text.get('1.0', tk.END).strip()
            self.current_link.notes = notes if notes else None

            # Update in database
            self.db_manager.update_link(
                link_id=self.current_link.id,
                title=self.current_link.title,
                notes=self.current_link.notes,
                is_favorite=self.current_link.is_favorite
            )

            # Update categories
            # First, remove all existing categories
            for category in self.current_link.categories:
                self.db_manager.remove_link_from_category(
                    self.current_link.id,
                    category.id
                )

            # Add selected categories
            for cat_id, (var, category) in self.category_vars.items():
                if var.get():
                    self.db_manager.add_link_to_category(
                        self.current_link.id,
                        cat_id
                    )

            # Update tags
            tag_text = self.tags_var.get().strip()
            new_tags = set()
            if tag_text:
                new_tags = {tag.strip() for tag in tag_text.split(',') if tag.strip()}

            # Get current tags
            current_tags = {tag.name for tag in self.current_link.tags}

            # Remove old tags
            for tag in self.current_link.tags:
                if tag.name not in new_tags:
                    self.db_manager.remove_tag_from_link(
                        self.current_link.id,
                        tag.id
                    )

            # Add new tags
            for tag_name in new_tags:
                if tag_name not in current_tags:
                    self.db_manager.add_tag_to_link(
                        self.current_link.id,
                        tag_name
                    )

            # Notify callback
            if self.on_save:
                self.on_save(self.current_link)

            messagebox.showinfo("Success", "Changes saved successfully")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save changes: {e}")

    def _revert_changes(self):
        """Revert changes to original values."""
        if self.current_link:
            # Reload link from database
            link = self.db_manager.get_link(self.current_link.id)
            self.set_link(link)

    def _delete_link(self):
        """Delete the current link."""
        if not self.current_link:
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete this link?\n\n{self.current_link.title}"):
            return

        try:
            # Delete from database
            if self.db_manager.delete_link(self.current_link.id):
                # Clear panel
                self.clear()

                # Notify callback
                if self.on_save:
                    self.on_save(None)

                messagebox.showinfo("Success", "Link deleted successfully")
            else:
                messagebox.showerror("Delete Error", "Failed to delete link")

        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete link: {e}")

    def _open_url(self):
        """Open the current URL in browser."""
        if self.current_link:
            webbrowser.open(self.current_link.url)