"""
Trash/Recycle Bin dialog for managing deleted links.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from datetime import datetime

from database.db_manager import DatabaseManager
from database.models import Link


class TrashDialog:
    """Dialog for viewing and managing deleted links."""

    def __init__(self, parent, db_manager: DatabaseManager, on_restore: Optional[Callable] = None):
        """Initialize the trash dialog.

        Args:
            parent: Parent window
            db_manager: Database manager instance
            on_restore: Callback when links are restored
        """
        self.db_manager = db_manager
        self.on_restore = on_restore
        self.selected_links = []

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🗑️ Recycle Bin - Deleted Links")
        self.dialog.geometry("900x600")
        self.dialog.resizable(True, True)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()
        self._load_deleted_links()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the UI components."""
        # Main container
        container = ttk.Frame(self.dialog, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Top toolbar
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Info label
        self.info_label = ttk.Label(toolbar, text="Loading deleted links...")
        self.info_label.pack(side=tk.LEFT)

        # Button frame (right side)
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(
            btn_frame,
            text="♻️ Restore Selected",
            command=self._restore_selected
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="🗑️ Permanently Delete",
            command=self._permanent_delete_selected
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="🔄 Refresh",
            command=self._load_deleted_links
        ).pack(side=tk.LEFT, padx=2)

        # Search frame
        search_frame = ttk.Frame(container)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self._search())

        ttk.Button(
            search_frame,
            text="🔍 Search",
            command=self._search
        ).pack(side=tk.LEFT)

        # Treeview for deleted links
        tree_frame = ttk.Frame(container)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Create treeview
        columns = ('title', 'url', 'deleted_at', 'access_count')
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode='extended'  # Allow multiple selection
        )

        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Column configuration
        self.tree.heading('#0', text='')
        self.tree.heading('title', text='Title')
        self.tree.heading('url', text='URL')
        self.tree.heading('deleted_at', text='Deleted')
        self.tree.heading('access_count', text='Visits')

        self.tree.column('#0', width=30, stretch=False)
        self.tree.column('title', width=250)
        self.tree.column('url', width=350)
        self.tree.column('deleted_at', width=150)
        self.tree.column('access_count', width=60)

        # Pack treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Bind double-click to restore
        self.tree.bind('<Double-Button-1>', lambda e: self._restore_selected())

        # Bottom button frame
        bottom_frame = ttk.Frame(container)
        bottom_frame.pack(fill=tk.X)

        ttk.Label(
            bottom_frame,
            text="💡 Tip: Double-click to restore, or select multiple items and use buttons",
            font=('', 9)
        ).pack(side=tk.LEFT)

        ttk.Button(
            bottom_frame,
            text="Close",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)

    def _load_deleted_links(self):
        """Load all deleted links from database."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get deleted links
        deleted_links = self.db_manager.get_links(include_deleted=True)
        # Filter only deleted ones
        deleted_links = [link for link in deleted_links if link.is_deleted]

        # Update info label
        self.info_label.config(text=f"Found {len(deleted_links)} deleted links")

        # Add to treeview
        for link in deleted_links:
            # Format deleted date
            if link.deleted_at:
                deleted_str = link.deleted_at.strftime('%Y-%m-%d %H:%M')
            else:
                deleted_str = 'Unknown'

            # Insert into tree
            item_id = self.tree.insert(
                '',
                'end',
                text='🗑️',
                values=(
                    link.title or link.url,
                    link.url,
                    deleted_str,
                    link.access_count
                ),
                tags=(link.id,)  # Store link ID in tags
            )

        self.selected_links = []

    def _search(self):
        """Search for deleted links."""
        query = self.search_var.get().strip()

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get deleted links with search
        if query:
            deleted_links = self.db_manager.get_links(
                search_query=query,
                include_deleted=True
            )
        else:
            deleted_links = self.db_manager.get_links(include_deleted=True)

        # Filter only deleted ones
        deleted_links = [link for link in deleted_links if link.is_deleted]

        # Update info label
        if query:
            self.info_label.config(text=f"Found {len(deleted_links)} deleted links matching '{query}'")
        else:
            self.info_label.config(text=f"Found {len(deleted_links)} deleted links")

        # Add to treeview
        for link in deleted_links:
            # Format deleted date
            if link.deleted_at:
                deleted_str = link.deleted_at.strftime('%Y-%m-%d %H:%M')
            else:
                deleted_str = 'Unknown'

            # Insert into tree
            self.tree.insert(
                '',
                'end',
                text='🗑️',
                values=(
                    link.title or link.url,
                    link.url,
                    deleted_str,
                    link.access_count
                ),
                tags=(link.id,)
            )

    def _get_selected_link_ids(self):
        """Get IDs of selected links."""
        selected_items = self.tree.selection()
        link_ids = []

        for item in selected_items:
            tags = self.tree.item(item)['tags']
            if tags:
                link_ids.append(tags[0])

        return link_ids

    def _restore_selected(self):
        """Restore selected links."""
        link_ids = self._get_selected_link_ids()

        if not link_ids:
            messagebox.showwarning("No Selection", "Please select links to restore")
            return

        # Confirm restoration
        count = len(link_ids)
        msg = f"Restore {count} link{'s' if count > 1 else ''}?"
        if not messagebox.askyesno("Confirm Restore", msg):
            return

        # Restore each link
        restored_count = 0
        for link_id in link_ids:
            if self.db_manager.restore_link(link_id):
                restored_count += 1

        # Show result
        if restored_count > 0:
            messagebox.showinfo(
                "Success",
                f"Restored {restored_count} link{'s' if restored_count > 1 else ''}"
            )

            # Reload list
            self._load_deleted_links()

            # Call callback if provided
            if self.on_restore:
                self.on_restore()
        else:
            messagebox.showerror("Error", "Failed to restore links")

    def _permanent_delete_selected(self):
        """Permanently delete selected links."""
        link_ids = self._get_selected_link_ids()

        if not link_ids:
            messagebox.showwarning("No Selection", "Please select links to permanently delete")
            return

        # Strong confirmation for permanent deletion
        count = len(link_ids)
        msg = f"⚠️ WARNING: Permanently delete {count} link{'s' if count > 1 else ''}?\n\n" \
              f"This action CANNOT be undone!"

        if not messagebox.askyesno("Confirm Permanent Deletion", msg, icon='warning'):
            return

        # Double confirmation for safety
        msg2 = "Are you ABSOLUTELY sure? This will permanently delete the selected links."
        if not messagebox.askyesno("Final Confirmation", msg2, icon='warning'):
            return

        # Permanently delete each link
        deleted_count = 0
        for link_id in link_ids:
            if self.db_manager.delete_link(link_id, permanent=True):
                deleted_count += 1

        # Show result
        if deleted_count > 0:
            messagebox.showinfo(
                "Deleted",
                f"Permanently deleted {deleted_count} link{'s' if deleted_count > 1 else ''}"
            )

            # Reload list
            self._load_deleted_links()
        else:
            messagebox.showerror("Error", "Failed to delete links")