"""
Category management dialog.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from typing import List

from database.db_manager import DatabaseManager
from database.models import Category


class CategoryDialog:
    """Dialog for managing categories."""

    def __init__(self, parent, db_manager: DatabaseManager):
        """Initialize the category dialog.

        Args:
            parent: Parent window
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.categories = []
        self.selected_category = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Categories")
        self.dialog.geometry("600x450")
        self.dialog.resizable(True, True)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()
        self._load_categories()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Bind ESC to close dialog
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def _build_ui(self):
        """Build the UI components."""
        # Main container
        container = ttk.Frame(self.dialog, padding="10")
        container.pack(fill=tk.BOTH, expand=True)

        # Left side: Category list
        list_frame = ttk.LabelFrame(container, text="Categories", padding="5")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.category_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            height=15
        )
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.category_listbox.yview)

        # Bind selection event
        self.category_listbox.bind('<<ListboxSelect>>', self._on_select)

        # Right side: Edit panel
        edit_frame = ttk.Frame(container)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        # Category name
        ttk.Label(edit_frame, text="Name:").pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(edit_frame, textvariable=self.name_var, width=30)
        self.name_entry.pack(pady=(0, 10), fill=tk.X)

        # Color selection
        ttk.Label(edit_frame, text="Color:").pack(anchor=tk.W, pady=(0, 5))

        color_frame = ttk.Frame(edit_frame)
        color_frame.pack(pady=(0, 10))

        self.color_var = tk.StringVar(value="#808080")
        self.color_label = tk.Label(
            color_frame,
            text="      ",
            bg=self.color_var.get(),
            relief=tk.SOLID,
            borderwidth=1,
            width=10
        )
        self.color_label.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            color_frame,
            text="Choose...",
            command=self._choose_color
        ).pack(side=tk.LEFT)

        # Statistics
        stats_frame = ttk.LabelFrame(edit_frame, text="Statistics", padding="5")
        stats_frame.pack(fill=tk.X, pady=(10, 10))

        self.stats_var = tk.StringVar(value="No category selected")
        ttk.Label(stats_frame, textvariable=self.stats_var).pack()

        # Buttons
        button_frame = ttk.Frame(edit_frame)
        button_frame.pack(pady=(10, 0))

        ttk.Button(
            button_frame,
            text="New",
            command=self._new_category,
            width=10
        ).grid(row=0, column=0, padx=2, pady=2)

        ttk.Button(
            button_frame,
            text="Save",
            command=self._save_category,
            width=10
        ).grid(row=0, column=1, padx=2, pady=2)

        ttk.Button(
            button_frame,
            text="Delete",
            command=self._delete_category,
            width=10
        ).grid(row=1, column=0, padx=2, pady=2)

        ttk.Button(
            button_frame,
            text="Close",
            command=self.dialog.destroy,
            width=10
        ).grid(row=1, column=1, padx=2, pady=2)

    def _load_categories(self):
        """Load categories from database."""
        self.categories = self.db_manager.get_categories()
        self._refresh_list()

    def _refresh_list(self):
        """Refresh the category list."""
        self.category_listbox.delete(0, tk.END)

        for category in self.categories:
            # Show hierarchy with indentation
            if category.parent_id:
                display_name = f"  → {category.name}"
            else:
                display_name = category.name

            self.category_listbox.insert(tk.END, display_name)

            # Set item color
            try:
                self.category_listbox.itemconfig(
                    tk.END,
                    foreground=category.color
                )
            except:
                pass  # Color might not be valid

    def _on_select(self, event):
        """Handle category selection."""
        selection = self.category_listbox.curselection()
        if not selection:
            self.selected_category = None
            self._clear_edit_panel()
            return

        index = selection[0]
        if index < len(self.categories):
            self.selected_category = self.categories[index]
            self._show_category_details()

    def _show_category_details(self):
        """Show selected category details."""
        if not self.selected_category:
            return

        self.name_var.set(self.selected_category.name)
        self.color_var.set(self.selected_category.color)
        self.color_label.config(bg=self.selected_category.color)

        # Get statistics
        # Count links in this category
        links = self.db_manager.get_links(category_id=self.selected_category.id)
        link_count = len(links)

        self.stats_var.set(f"{link_count} links in this category")

    def _clear_edit_panel(self):
        """Clear the edit panel."""
        self.name_var.set("")
        self.color_var.set("#808080")
        self.color_label.config(bg="#808080")
        self.stats_var.set("No category selected")

    def _choose_color(self):
        """Show color chooser dialog."""
        current_color = self.color_var.get()
        color = colorchooser.askcolor(initialcolor=current_color)

        if color[1]:  # color[1] is the hex value
            self.color_var.set(color[1])
            self.color_label.config(bg=color[1])

    def _new_category(self):
        """Create a new category."""
        # Clear selection and edit panel
        self.category_listbox.selection_clear(0, tk.END)
        self.selected_category = None
        self._clear_edit_panel()

        # Focus on name entry
        self.name_entry.focus_set()

    def _save_category(self):
        """Save category changes."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Invalid Name", "Category name cannot be empty")
            return

        color = self.color_var.get()

        try:
            if self.selected_category:
                # Update existing category
                success = self.db_manager.update_category(
                    self.selected_category.id,
                    name=name,
                    color=color
                )
                if success:
                    self.selected_category.name = name
                    self.selected_category.color = color
                    messagebox.showinfo("Success", "Category updated successfully")
            else:
                # Create new category
                new_category = self.db_manager.create_category(
                    name=name,
                    color=color
                )
                messagebox.showinfo("Success", f"Category '{name}' created successfully")

            # Reload categories
            self._load_categories()

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save category: {e}")

    def _delete_category(self):
        """Delete the selected category."""
        if not self.selected_category:
            messagebox.showwarning("No Selection", "Please select a category to delete")
            return

        # Check if category has links
        links = self.db_manager.get_links(category_id=self.selected_category.id)
        if links:
            msg = f"Category '{self.selected_category.name}' has {len(links)} links.\n\n" \
                  f"Deleting this category will remove it from all linked items.\n\n" \
                  f"Continue?"
        else:
            msg = f"Delete category '{self.selected_category.name}'?"

        if not messagebox.askyesno("Confirm Delete", msg):
            return

        try:
            if self.db_manager.delete_category(self.selected_category.id):
                messagebox.showinfo("Success", "Category deleted successfully")
                self._load_categories()
                self._clear_edit_panel()
            else:
                messagebox.showerror("Delete Error", "Failed to delete category")

        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete category: {e}")