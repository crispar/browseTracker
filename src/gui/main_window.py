"""
Main application window for Browser Link Tracker.
"""

import tkinter as tk
from tkinter import ttk, messagebox, Menu
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import webbrowser

from database.db_manager import DatabaseManager
# Use optimized version if available, fallback to regular
try:
    from tracker.browser_history_optimized import OptimizedHistoryTracker as HistoryTracker
except ImportError:
    from tracker.browser_history import HistoryTracker
from utils.config import get_config
from gui.link_list import LinkListView
from gui.detail_panel import DetailPanel
from gui.category_dialog import CategoryDialog

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window."""

    def __init__(self):
        """Initialize the main window."""
        self.root = tk.Tk()
        self.root.title("Browser Link Tracker")

        # Load configuration
        self.config = get_config()
        self.root.geometry(self.config.get('window_geometry', '1200x700'))

        # Initialize database
        self.db_manager = DatabaseManager()

        # Initialize tracker
        self.tracker = HistoryTracker(self.db_manager)

        # Current filter/search state
        self.current_search = ""
        self.current_category = None
        self.current_days_filter = None

        # Scan timer
        self.scan_timer = None
        self.is_scanning = False

        # Build UI
        self._build_ui()

        # Initialize browser profiles
        self._initialize_browsers()

        # Load initial data
        self.refresh_links()

        # Start auto-scan if enabled
        if self.config.auto_scan:
            self._schedule_scan()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        """Build the user interface."""
        # Create menu bar
        self._create_menu()

        # Create toolbar
        self._create_toolbar()

        # Create main content area with paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left side: Link list
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # Create link list view
        self.link_list = LinkListView(
            left_frame,
            on_select=self.on_link_selected,
            on_double_click=self.on_link_double_click
        )
        self.link_list.pack(fill=tk.BOTH, expand=True)

        # Right side: Detail panel
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # Create detail panel
        self.detail_panel = DetailPanel(
            right_frame,
            db_manager=self.db_manager,
            on_save=self.on_detail_save
        )
        self.detail_panel.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self._create_status_bar()

    def _create_menu(self):
        """Create the menu bar."""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Scan Now", command=self.scan_now, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Export...", command=self.export_data)
        file_menu.add_command(label="Import...", command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Categories...", command=self.show_category_dialog)
        edit_menu.add_command(label="Delete Selected", command=self.delete_selected, accelerator="Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences...", command=self.show_preferences)

        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_links, accelerator="Ctrl+R")
        view_menu.add_separator()
        view_menu.add_command(label="Show All", command=lambda: self.filter_by_days(None))
        view_menu.add_command(label="Today", command=lambda: self.filter_by_days(1))
        view_menu.add_command(label="Last 7 Days", command=lambda: self.filter_by_days(7))
        view_menu.add_command(label="Last 30 Days", command=lambda: self.filter_by_days(30))

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind('<F5>', lambda e: self.scan_now())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<Control-r>', lambda e: self.refresh_links())

    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # Scan button
        self.scan_button = ttk.Button(
            toolbar,
            text="📡 Scan",
            command=self.scan_now,
            width=10
        )
        self.scan_button.pack(side=tk.LEFT, padx=2)

        # Category filter
        ttk.Label(toolbar, text="Category:").pack(side=tk.LEFT, padx=(10, 2))
        self.category_combo = ttk.Combobox(
            toolbar,
            state="readonly",
            width=20
        )
        self.category_combo.pack(side=tk.LEFT, padx=2)
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_filter)

        # Time filter buttons
        ttk.Label(toolbar, text="Show:").pack(side=tk.LEFT, padx=(10, 2))

        time_filters = [
            ("All", None),
            ("Today", 1),
            ("7 Days", 7),
            ("30 Days", 30)
        ]

        self.time_filter_var = tk.StringVar(value="All")
        for label, days in time_filters:
            ttk.Radiobutton(
                toolbar,
                text=label,
                variable=self.time_filter_var,
                value=label,
                command=lambda d=days: self.filter_by_days(d)
            ).pack(side=tk.LEFT, padx=2)

        # Search box
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(10, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            toolbar,
            textvariable=self.search_var,
            width=30
        )
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind('<Return>', self.on_search)
        self.search_entry.bind('<KeyRelease>', self.on_search_key)

        # Search button
        ttk.Button(
            toolbar,
            text="🔍",
            command=self.on_search,
            width=3
        ).pack(side=tk.LEFT)

        # Clear button
        ttk.Button(
            toolbar,
            text="✖",
            command=self.clear_search,
            width=3
        ).pack(side=tk.LEFT)

    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Status text
        self.status_text = tk.StringVar(value="Ready")
        ttk.Label(
            self.status_bar,
            textvariable=self.status_text
        ).pack(side=tk.LEFT, padx=5)

        # Link count
        self.link_count_text = tk.StringVar(value="0 links")
        ttk.Label(
            self.status_bar,
            textvariable=self.link_count_text
        ).pack(side=tk.RIGHT, padx=5)

        # Scan status
        self.scan_status_text = tk.StringVar(value="")
        ttk.Label(
            self.status_bar,
            textvariable=self.scan_status_text
        ).pack(side=tk.RIGHT, padx=5)

    def _initialize_browsers(self):
        """Initialize browser profiles."""
        try:
            profiles = self.tracker.initialize()
            self.set_status(f"Found {len(profiles)} browser profiles")

            # Update category filter combo
            self._update_category_filter()

        except Exception as e:
            logger.error(f"Error initializing browsers: {e}")
            self.set_status("Error initializing browsers")

    def _update_category_filter(self):
        """Update category filter dropdown."""
        categories = self.db_manager.get_categories()
        category_names = ["All Categories"] + [cat.name for cat in categories]
        self.category_combo['values'] = category_names
        self.category_combo.set("All Categories")

    def refresh_links(self):
        """Refresh the link list."""
        try:
            # Get filter parameters
            category_id = None
            if self.current_category:
                # Look up category ID by name
                categories = self.db_manager.get_categories()
                for cat in categories:
                    if cat.name == self.current_category:
                        category_id = cat.id
                        break

            # Get links from database
            # Only apply limit when not searching or filtering
            limit = None
            if not self.current_search and not self.current_days_filter and not category_id:
                # When showing ALL links with no filters
                limit = None  # Show all links when "All" is selected
            else:
                # Apply reasonable limit when filtering
                limit = None

            links = self.db_manager.get_links(
                category_id=category_id,
                search_query=self.current_search if self.current_search else None,
                days_back=self.current_days_filter,
                sort_by='last_accessed_at',
                sort_desc=True,
                limit=limit
            )

            # Update link list
            self.link_list.set_links(links)

            # Update status
            self.link_count_text.set(f"{len(links)} links")

        except Exception as e:
            logger.error(f"Error refreshing links: {e}")
            self.set_status("Error loading links")

    def scan_now(self):
        """Start a browser history scan."""
        if self.is_scanning:
            self.set_status("Scan already in progress")
            return

        self.is_scanning = True
        self.scan_button.config(state='disabled')
        self.set_status("Scanning browser history...")
        self.scan_status_text.set("Scanning...")

        # Run scan in background thread
        thread = threading.Thread(target=self._run_scan)
        thread.daemon = True
        thread.start()

    def _run_scan(self):
        """Run the actual scan (in background thread)."""
        try:
            # Use optimized method if available
            if hasattr(self.tracker, 'scan_and_update_batch'):
                # Optimized batch scan with more items
                stats = self.tracker.scan_and_update_batch(since_hours=24, max_items=1000)
            else:
                # Fallback to regular scan
                stats = self.tracker.scan_and_update(since_hours=24)  # Last 24 hours for performance

            # Calculate totals
            total_new = sum(s.get('new', 0) for s in stats.values() if isinstance(s, dict))
            total_updated = sum(s.get('updated', 0) for s in stats.values() if isinstance(s, dict))

            # Update UI in main thread
            self.root.after(0, self._scan_complete, total_new, total_updated)

        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.root.after(0, self._scan_error, str(e))

    def _scan_complete(self, new_count: int, updated_count: int):
        """Handle scan completion (in main thread)."""
        self.is_scanning = False
        self.scan_button.config(state='normal')
        self.scan_status_text.set(f"Last scan: {datetime.now().strftime('%H:%M')}")

        if new_count > 0 or updated_count > 0:
            self.set_status(f"Scan complete: {new_count} new, {updated_count} updated")
            self.refresh_links()
        else:
            self.set_status("Scan complete: No new links")

    def _scan_error(self, error_msg: str):
        """Handle scan error (in main thread)."""
        self.is_scanning = False
        self.scan_button.config(state='normal')
        self.scan_status_text.set("")
        self.set_status(f"Scan error: {error_msg}")

    def _schedule_scan(self):
        """Schedule the next automatic scan."""
        if self.scan_timer:
            self.root.after_cancel(self.scan_timer)

        if self.config.auto_scan:
            interval = self.config.scan_interval * 1000  # Convert to milliseconds
            self.scan_timer = self.root.after(interval, self._auto_scan)

    def _auto_scan(self):
        """Perform automatic scan."""
        if not self.is_scanning:
            self.scan_now()
        self._schedule_scan()

    def on_link_selected(self, link):
        """Handle link selection."""
        if link:
            self.detail_panel.set_link(link)

    def on_link_double_click(self, link):
        """Handle link double-click (open in browser)."""
        if link:
            webbrowser.open(link.url)
            self.set_status(f"Opened: {link.title}")

    def on_detail_save(self, link):
        """Handle detail panel save."""
        self.refresh_links()
        self.set_status("Changes saved")

    def on_category_filter(self, event=None):
        """Handle category filter change."""
        selected = self.category_combo.get()
        if selected == "All Categories":
            self.current_category = None
        else:
            self.current_category = selected
        self.refresh_links()

    def filter_by_days(self, days: Optional[int]):
        """Filter links by time period."""
        self.current_days_filter = days
        if days is None:
            self.time_filter_var.set("All")
        elif days == 1:
            self.time_filter_var.set("Today")
        elif days == 7:
            self.time_filter_var.set("7 Days")
        elif days == 30:
            self.time_filter_var.set("30 Days")
        self.refresh_links()

    def on_search(self, event=None):
        """Handle search."""
        self.current_search = self.search_var.get().strip()
        self.refresh_links()

    def on_search_key(self, event=None):
        """Handle search key press (live search)."""
        # Only search if more than 2 characters or empty
        search_text = self.search_var.get().strip()
        if len(search_text) == 0 or len(search_text) > 2:
            self.current_search = search_text
            self.refresh_links()

    def clear_search(self):
        """Clear search and filters."""
        self.search_var.set("")
        self.current_search = ""
        self.current_category = None
        self.current_days_filter = None
        self.category_combo.set("All Categories")
        self.time_filter_var.set("All")
        self.refresh_links()

    def delete_selected(self):
        """Delete selected links."""
        selected_links = self.link_list.get_selected_links()
        if not selected_links:
            return

        # Confirm deletion
        count = len(selected_links)
        msg = f"Delete {count} selected link{'s' if count > 1 else ''}?"
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        # Delete links
        deleted = 0
        for link in selected_links:
            if self.db_manager.delete_link(link.id):
                deleted += 1

        self.refresh_links()
        self.set_status(f"Deleted {deleted} links")

    def show_category_dialog(self):
        """Show category management dialog."""
        dialog = CategoryDialog(self.root, self.db_manager)
        self.root.wait_window(dialog.dialog)

        # Refresh after dialog closes
        self._update_category_filter()
        self.refresh_links()

    def show_preferences(self):
        """Show preferences dialog."""
        # TODO: Implement preferences dialog
        messagebox.showinfo("Preferences", "Preferences dialog not implemented yet")

    def export_data(self):
        """Export data to file."""
        from tkinter import filedialog
        import json

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                data = self.db_manager.export_to_dict()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.set_status(f"Exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def import_data(self):
        """Import data from file."""
        # TODO: Implement import functionality
        messagebox.showinfo("Import", "Import functionality not implemented yet")

    def show_about(self):
        """Show about dialog."""
        about_text = """Browser Link Tracker
Version 0.1.0

A personal link management tool that tracks
browsing history across multiple browsers.

© 2024 - Personal Use"""

        messagebox.showinfo("About", about_text)

    def set_status(self, message: str):
        """Set status bar message."""
        self.status_text.set(message)

    def on_closing(self):
        """Handle window closing."""
        # Cancel scan timer
        if self.scan_timer:
            self.root.after_cancel(self.scan_timer)

        # Save window geometry
        self.config.set('window_geometry', self.root.geometry())

        # Close database
        self.db_manager.close()

        # Destroy window
        self.root.destroy()

    def run(self):
        """Start the application."""
        self.root.mainloop()