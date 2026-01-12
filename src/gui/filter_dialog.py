"""
URL Filter management dialog.
Allows users to create, edit, and manage URL filters to exclude certain domains from tracking.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class FilterDialog:
    """Dialog for managing URL filters."""

    def __init__(self, parent, db_manager, on_update: Optional[Callable] = None):
        """Initialize the filter dialog.

        Args:
            parent: Parent window
            db_manager: Database manager instance
            on_update: Optional callback when filters are updated
        """
        self.db_manager = db_manager
        self.on_update = on_update

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("URL Filters - Exclude from Tracking")
        self.dialog.geometry("800x500")
        self.dialog.minsize(600, 400)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._load_filters()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Bind ESC to close dialog
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def _create_widgets(self):
        """Create and layout dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.dialog.grid_rowconfigure(0, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Title and description
        title = ttk.Label(main_frame, text="URL Filters", font=('', 12, 'bold'))
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        desc = ttk.Label(main_frame,
                        text="Add patterns to exclude URLs from being tracked. For example, 'sts.secosso.net' will exclude all URLs from that domain.",
                        wraplength=750)
        desc.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))

        # Filter list frame
        list_frame = ttk.LabelFrame(main_frame, text="Active Filters", padding="10")
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        # Treeview for filters
        columns = ('Pattern', 'Type', 'Description', 'Status')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)

        # Define columns
        self.tree.column('Pattern', width=250)
        self.tree.column('Type', width=100)
        self.tree.column('Description', width=300)
        self.tree.column('Status', width=80)

        # Define headings
        self.tree.heading('Pattern', text='Pattern')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Description', text='Description')
        self.tree.heading('Status', text='Status')

        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))

        # Add filter button
        add_btn = ttk.Button(button_frame, text="Add Filter", command=self._add_filter)
        add_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Edit filter button
        edit_btn = ttk.Button(button_frame, text="Edit", command=self._edit_filter)
        edit_btn.pack(side=tk.LEFT, padx=5)

        # Toggle active/inactive button
        toggle_btn = ttk.Button(button_frame, text="Enable/Disable", command=self._toggle_filter)
        toggle_btn.pack(side=tk.LEFT, padx=5)

        # Delete filter button
        delete_btn = ttk.Button(button_frame, text="Delete", command=self._delete_filter)
        delete_btn.pack(side=tk.LEFT, padx=5)

        # Test filter button
        test_btn = ttk.Button(button_frame, text="Test Filter", command=self._test_filter)
        test_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn = ttk.Button(button_frame, text="Close", command=self.dialog.destroy)
        close_btn.pack(side=tk.RIGHT)

        # Bind double-click to edit
        self.tree.bind('<Double-Button-1>', lambda e: self._edit_filter())

    def _load_filters(self):
        """Load filters from database."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get all filters (including inactive ones)
        filters = self.db_manager.get_filters(active_only=False)

        # Add to tree
        for filter_obj in filters:
            status = "Active" if filter_obj.is_active else "Inactive"
            values = (filter_obj.pattern, filter_obj.filter_type,
                     filter_obj.description or "", status)

            # Add with tag for styling inactive filters
            tags = () if filter_obj.is_active else ('inactive',)
            item = self.tree.insert('', tk.END, values=values, tags=tags)

            # Store filter object as item data
            self.tree.set(item, 'Pattern', filter_obj.pattern)
            self.tree.item(item, tags=tags + (str(filter_obj.id),))

        # Style inactive items
        self.tree.tag_configure('inactive', foreground='gray')

    def _add_filter(self):
        """Add a new filter."""
        dialog = FilterEditDialog(self.dialog, self.db_manager)
        if dialog.result:
            pattern, filter_type, description = dialog.result
            try:
                self.db_manager.create_filter(
                    pattern=pattern,
                    filter_type=filter_type,
                    description=description,
                    is_active=True
                )
                self._load_filters()
                if self.on_update:
                    self.on_update()
                messagebox.showinfo("Success", f"Filter '{pattern}' added successfully")
            except Exception as e:
                if "UNIQUE" in str(e):
                    messagebox.showerror("Error", f"Filter '{pattern}' already exists")
                else:
                    messagebox.showerror("Error", f"Failed to add filter: {e}")

    def _edit_filter(self):
        """Edit selected filter."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a filter to edit")
            return

        item = selection[0]
        values = self.tree.item(item, 'values')
        pattern = values[0]
        filter_type = values[1]
        description = values[2]

        # Get filter ID from tags
        tags = self.tree.item(item, 'tags')
        filter_id = None
        for tag in tags:
            if tag.isdigit():
                filter_id = int(tag)
                break

        if not filter_id:
            messagebox.showerror("Error", "Could not identify filter")
            return

        dialog = FilterEditDialog(self.dialog, self.db_manager,
                                 pattern, filter_type, description)
        if dialog.result:
            new_pattern, new_type, new_description = dialog.result
            try:
                self.db_manager.update_filter(
                    filter_id,
                    pattern=new_pattern,
                    filter_type=new_type,
                    description=new_description
                )
                self._load_filters()
                if self.on_update:
                    self.on_update()
                messagebox.showinfo("Success", "Filter updated successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update filter: {e}")

    def _toggle_filter(self):
        """Toggle filter active/inactive status."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a filter to toggle")
            return

        item = selection[0]
        values = self.tree.item(item, 'values')
        current_status = values[3]

        # Get filter ID from tags
        tags = self.tree.item(item, 'tags')
        filter_id = None
        for tag in tags:
            if tag.isdigit():
                filter_id = int(tag)
                break

        if not filter_id:
            messagebox.showerror("Error", "Could not identify filter")
            return

        new_status = current_status != "Active"
        try:
            self.db_manager.update_filter(filter_id, is_active=new_status)
            self._load_filters()
            if self.on_update:
                self.on_update()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle filter: {e}")

    def _delete_filter(self):
        """Delete selected filter."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a filter to delete")
            return

        item = selection[0]
        values = self.tree.item(item, 'values')
        pattern = values[0]

        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete filter '{pattern}'?"):
            return

        # Get filter ID from tags
        tags = self.tree.item(item, 'tags')
        filter_id = None
        for tag in tags:
            if tag.isdigit():
                filter_id = int(tag)
                break

        if not filter_id:
            messagebox.showerror("Error", "Could not identify filter")
            return

        try:
            self.db_manager.delete_filter(filter_id)
            self._load_filters()
            if self.on_update:
                self.on_update()
            messagebox.showinfo("Success", "Filter deleted successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete filter: {e}")

    def _test_filter(self):
        """Test a filter with a sample URL."""
        url = simpledialog.askstring("Test Filter",
                                     "Enter a URL to test against filters:")
        if not url:
            return

        if self.db_manager.should_track_url(url):
            messagebox.showinfo("Test Result",
                               f"URL '{url}' will be TRACKED\n\n"
                               "This URL does not match any active filter.")
        else:
            # Find which filter matched
            filters = self.db_manager.get_filters(active_only=True)
            matched = None
            for filter_obj in filters:
                if filter_obj.matches(url):
                    matched = filter_obj
                    break

            if matched:
                messagebox.showinfo("Test Result",
                                   f"URL '{url}' will be EXCLUDED\n\n"
                                   f"Matched filter: '{matched.pattern}' (Type: {matched.filter_type})")
            else:
                messagebox.showinfo("Test Result",
                                   f"URL '{url}' will be EXCLUDED")


class FilterEditDialog:
    """Dialog for adding/editing a filter."""

    def __init__(self, parent, db_manager, pattern="", filter_type="domain", description=""):
        """Initialize the edit dialog."""
        self.db_manager = db_manager
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add/Edit Filter")
        self.dialog.geometry("500x350")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Create widgets
        self._create_widgets(pattern, filter_type, description)

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Bind ESC to close dialog
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

        # Focus on pattern entry
        self.pattern_entry.focus()

        # Wait for dialog
        self.dialog.wait_window()

    def _create_widgets(self, pattern, filter_type, description):
        """Create dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Pattern entry
        ttk.Label(main_frame, text="Pattern:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pattern_entry = ttk.Entry(main_frame, width=50)
        self.pattern_entry.grid(row=0, column=1, pady=5)
        self.pattern_entry.insert(0, pattern)

        # Filter type
        ttk.Label(main_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value=filter_type)
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=5)

        types = [
            ("Domain", "domain", "Match exact domain and subdomains"),
            ("Prefix", "prefix", "Match URLs starting with pattern"),
            ("Contains", "contains", "Match URLs containing pattern"),
            ("Regex", "regex", "Regular expression pattern")
        ]

        for i, (label, value, tooltip) in enumerate(types):
            rb = ttk.Radiobutton(type_frame, text=label, variable=self.type_var, value=value)
            rb.grid(row=i//2, column=i%2, sticky=tk.W, padx=(0, 20))

        # Description
        ttk.Label(main_frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.desc_entry = ttk.Entry(main_frame, width=50)
        self.desc_entry.grid(row=2, column=1, pady=5)
        self.desc_entry.insert(0, description)

        # Examples
        examples_frame = ttk.LabelFrame(main_frame, text="Examples", padding="10")
        examples_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        examples = [
            "Domain: 'sts.secosso.net' - Excludes all URLs from this domain",
            "Prefix: 'https://internal.' - Excludes URLs starting with this",
            "Contains: 'analytics' - Excludes URLs containing 'analytics'",
            "Regex: '^https?://localhost' - Excludes localhost URLs"
        ]

        for i, example in enumerate(examples):
            ttk.Label(examples_frame, text=example, font=('', 9)).pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="OK", command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT)

        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._ok())

    def _ok(self):
        """Handle OK button."""
        pattern = self.pattern_entry.get().strip()
        if not pattern:
            messagebox.showerror("Error", "Pattern is required")
            return

        self.result = (
            pattern,
            self.type_var.get(),
            self.desc_entry.get().strip()
        )
        self.dialog.destroy()