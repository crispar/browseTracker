"""
Link list view component using Tkinter Treeview.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Optional, Callable

from database.models import Link
from utils.config import get_config


class LinkListView(ttk.Frame):
    """Tree view for displaying links."""

    def __init__(self, parent, on_select: Optional[Callable] = None,
                 on_double_click: Optional[Callable] = None):
        """Initialize the link list view.

        Args:
            parent: Parent widget
            on_select: Callback when a link is selected
            on_double_click: Callback when a link is double-clicked
        """
        super().__init__(parent)

        self.config = get_config()
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.links = []
        self.link_map = {}  # Map tree items to Link objects

        self._build_ui()

    def _build_ui(self):
        """Build the UI components."""
        # Create Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Create Treeview
        columns = []
        display_columns = []

        # Define columns based on config
        column_defs = [
            ('favorite', '❤', 30),
            ('title', 'Title', 300),
            ('url', 'URL', 300),
            ('categories', 'Categories', 150),
            ('tags', 'Tags', 150),
            ('last_accessed', 'Last Accessed', 150),
            ('access_count', 'Count', 60),
            ('browser', 'Browser', 100),
        ]

        for col_id, col_name, default_width in column_defs:
            columns.append(col_id)
            if self.config.get(f'columns_visible.{col_id}', True):
                display_columns.append(col_id)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            displaycolumns=display_columns,
            show='tree headings',
            selectmode='extended'
        )

        # Configure scrollbars
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        self.tree.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Configure columns
        self.tree.column('#0', width=0, stretch=False)  # Hide tree column

        for col_id, col_name, default_width in column_defs:
            width = self.config.get(f'column_widths.{col_id}', default_width)
            self.tree.column(col_id, width=width, minwidth=30)
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_by_column(c))

        # Style alternating rows
        self.tree.tag_configure('oddrow', background='#f0f0f0')
        self.tree.tag_configure('favorite', foreground='#d00000')

        # Bind events
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-Button-1>', self._on_double_click)
        self.tree.bind('<Button-3>', self._on_right_click)  # Right-click

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Create context menu
        self._create_context_menu()

    def _create_context_menu(self):
        """Create right-click context menu."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open in Browser", command=self._open_selected)
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Toggle Favorite", command=self._toggle_favorite)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self._delete_selected)

    def set_links(self, links: List[Link]):
        """Set the links to display.

        Args:
            links: List of Link objects
        """
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        self.links = links
        self.link_map = {}

        # Limit display for performance
        # TODO: Implement virtual scrolling or pagination
        max_display = 2000  # Display up to 2000 items for reasonable performance
        display_links = links[:max_display] if len(links) > max_display else links

        # Add links to tree
        added_count = 0
        error_count = 0

        # Process in smaller batches to avoid GUI freezing
        batch_size = 100

        for batch_start in range(0, len(display_links), batch_size):
            batch_end = min(batch_start + batch_size, len(display_links))

            for i in range(batch_start, batch_end):
                if i >= len(display_links):
                    break

                link = display_links[i]
                try:
                    # Get values - this should never fail now with the new implementation
                    values = self._get_link_values(link)
                    tags = ('oddrow',) if i % 2 else ()
                    if link.is_favorite:
                        tags = tags + ('favorite',)

                    item = self.tree.insert('', 'end', values=values, tags=tags)
                    self.link_map[item] = link
                    added_count += 1
                except Exception as e:
                    # Skip this link if there's an error
                    error_count += 1
                    continue

            # Update GUI every batch to prevent freezing
            if hasattr(self, 'update'):
                self.update()

    def _get_link_values(self, link: Link) -> list:
        """Get display values for a link.

        Args:
            link: Link object

        Returns:
            List of values for tree columns
        """
        # Format dates
        date_format = self.config.get('date_format', '%Y-%m-%d %H:%M')
        last_accessed = ''
        if link.last_accessed_at:
            try:
                last_accessed = link.last_accessed_at.strftime(date_format)
            except:
                last_accessed = ''

        # Format categories and tags safely
        try:
            categories = ', '.join(cat.name for cat in link.categories)
        except:
            categories = ''

        try:
            tags = ', '.join(tag.name for tag in link.tags)
        except:
            tags = ''

        # Get title and URL - keep Unicode for proper display
        max_title_length = self.config.get('max_title_length', 80)

        # Keep original title and URL (including Korean/Unicode characters)
        title = link.title or link.url or "Unknown"
        url = link.url or ""

        # Truncate if needed
        if len(title) > max_title_length:
            title = title[:max_title_length - 3] + '...'

        return [
            '♥' if link.is_favorite else '',  # Heart symbol for favorites
            title,  # Keep original title with Unicode/Korean
            url,    # Keep original URL
            categories,
            tags,
            last_accessed,
            str(link.access_count) if link.access_count else '0',
            ''  # Browser info not stored directly on Link yet
        ]

    def get_selected_links(self) -> List[Link]:
        """Get currently selected links.

        Returns:
            List of selected Link objects
        """
        selected = []
        for item in self.tree.selection():
            if item in self.link_map:
                selected.append(self.link_map[item])
        return selected

    def _on_select(self, event):
        """Handle selection change."""
        selected = self.get_selected_links()
        if self.on_select and len(selected) == 1:
            self.on_select(selected[0])

    def _on_double_click(self, event):
        """Handle double-click."""
        selected = self.get_selected_links()
        if self.on_double_click and len(selected) == 1:
            self.on_double_click(selected[0])

    def _on_right_click(self, event):
        """Handle right-click for context menu."""
        # Select item under cursor
        item = self.tree.identify('item', event.x, event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _open_selected(self):
        """Open selected links in browser."""
        import webbrowser
        for link in self.get_selected_links():
            webbrowser.open(link.url)

    def _copy_url(self):
        """Copy selected URL to clipboard."""
        selected = self.get_selected_links()
        if selected:
            self.clipboard_clear()
            self.clipboard_append(selected[0].url)
            self.update()  # Required for clipboard

    def _toggle_favorite(self):
        """Toggle favorite status of selected links."""
        # This should be implemented with database callback
        pass

    def _delete_selected(self):
        """Delete selected links."""
        # This should be implemented with database callback
        pass

    def _sort_by_column(self, column: str):
        """Sort tree by column.

        Args:
            column: Column identifier to sort by
        """
        # Get current data
        data = []
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            link = self.link_map.get(child)
            data.append((child, values, link))

        # Determine sort key
        col_index = {
            'favorite': 0,
            'title': 1,
            'url': 2,
            'categories': 3,
            'tags': 4,
            'last_accessed': 5,
            'access_count': 6,
            'browser': 7
        }

        if column in col_index:
            idx = col_index[column]

            # Special handling for different column types
            if column == 'access_count':
                # Sort numerically
                data.sort(key=lambda x: int(x[1][idx]) if x[1][idx] else 0, reverse=True)
            elif column == 'last_accessed':
                # Sort by actual datetime
                data.sort(key=lambda x: x[2].last_accessed_at if x[2] else datetime.min, reverse=True)
            elif column == 'favorite':
                # Sort by boolean
                data.sort(key=lambda x: x[2].is_favorite if x[2] else False, reverse=True)
            else:
                # Sort alphabetically
                data.sort(key=lambda x: x[1][idx].lower() if x[1][idx] else '')

        # Reorder items
        for i, (child, values, link) in enumerate(data):
            self.tree.move(child, '', i)
            # Update row styling
            tags = ('oddrow',) if i % 2 else ()
            if link and link.is_favorite:
                tags = tags + ('favorite',)
            self.tree.item(child, tags=tags)