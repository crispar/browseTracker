"""Settings dialog for Browser Link Tracker."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import logging

from utils.settings import SettingsManager
from utils.browser_utils import BrowserManager

logger = logging.getLogger(__name__)


class SettingsDialog:
    """Settings dialog for configuring application preferences."""

    def __init__(self, parent, settings_manager: SettingsManager):
        """Initialize settings dialog.

        Args:
            parent: Parent window
            settings_manager: Settings manager instance
        """
        self.parent = parent
        self.settings_manager = settings_manager
        self.browser_manager = BrowserManager()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Store original settings to detect changes
        self.original_settings = settings_manager.get_all()
        self.changed = False

        self._create_widgets()
        self._load_settings()

        # Position dialog
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Bind ESC to cancel
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())

    def _create_widgets(self):
        """Create and layout dialog widgets."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General tab
        self._create_general_tab()

        # Browser tab
        self._create_browser_tab()

        # Display tab
        self._create_display_tab()

        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            button_frame,
            text="Apply",
            command=self._on_apply
        ).pack(side=tk.RIGHT)

        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._on_reset
        ).pack(side=tk.LEFT)

    def _create_general_tab(self):
        """Create general settings tab."""
        general_frame = ttk.Frame(self.notebook)
        self.notebook.add(general_frame, text="General")

        # Auto scan settings
        scan_frame = ttk.LabelFrame(general_frame, text="Auto Scan", padding=10)
        scan_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.auto_scan_var = tk.BooleanVar()
        ttk.Checkbutton(
            scan_frame,
            text="Enable automatic scanning",
            variable=self.auto_scan_var,
            command=self._on_setting_changed
        ).pack(anchor=tk.W)

        interval_frame = ttk.Frame(scan_frame)
        interval_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(interval_frame, text="Scan interval:").pack(side=tk.LEFT)
        self.scan_interval_var = tk.IntVar()
        ttk.Spinbox(
            interval_frame,
            from_=10,
            to=3600,
            textvariable=self.scan_interval_var,
            width=10,
            command=self._on_setting_changed
        ).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(interval_frame, text="seconds").pack(side=tk.LEFT, padx=(5, 0))

        # Startup settings
        startup_frame = ttk.LabelFrame(general_frame, text="Startup", padding=10)
        startup_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_minimized_var = tk.BooleanVar()
        ttk.Checkbutton(
            startup_frame,
            text="Start minimized",
            variable=self.start_minimized_var,
            command=self._on_setting_changed
        ).pack(anchor=tk.W)

        self.minimize_to_tray_var = tk.BooleanVar()
        ttk.Checkbutton(
            startup_frame,
            text="Minimize to system tray",
            variable=self.minimize_to_tray_var,
            command=self._on_setting_changed,
            state='disabled'  # Not implemented yet
        ).pack(anchor=tk.W)

        # Behavior settings
        behavior_frame = ttk.LabelFrame(general_frame, text="Behavior", padding=10)
        behavior_frame.pack(fill=tk.X, padx=10, pady=5)

        self.confirm_delete_var = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame,
            text="Confirm before deleting links",
            variable=self.confirm_delete_var,
            command=self._on_setting_changed
        ).pack(anchor=tk.W)

    def _create_browser_tab(self):
        """Create browser settings tab."""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="Browser")

        # Default browser selection
        default_frame = ttk.LabelFrame(browser_frame, text="Default Browser", padding=10)
        default_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(
            default_frame,
            text="Choose the browser to use when double-clicking links:"
        ).pack(anchor=tk.W, pady=(0, 10))

        # Get available browsers
        self.browser_var = tk.StringVar()
        browsers = self.browser_manager.get_browser_list()

        for browser_id, browser_name in browsers:
            ttk.Radiobutton(
                default_frame,
                text=browser_name,
                variable=self.browser_var,
                value=browser_id,
                command=self._on_setting_changed
            ).pack(anchor=tk.W, pady=2)

        # Browser detection info
        info_frame = ttk.LabelFrame(browser_frame, text="Detected Browsers", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create text widget for browser info
        info_text = tk.Text(info_frame, height=8, width=50, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True)

        # Show detected browsers
        detected = self.browser_manager.detect_installed_browsers()
        info_text.insert('1.0', "The following browsers were detected on your system:\n\n")

        for browser_id, info in detected.items():
            if browser_id != 'system':
                info_text.insert('end', f"• {info['name']}\n")
                if info['path']:
                    info_text.insert('end', f"  Location: {info['path']}\n\n")

        info_text.config(state='disabled')

    def _create_display_tab(self):
        """Create display settings tab."""
        display_frame = ttk.Frame(self.notebook)
        self.notebook.add(display_frame, text="Display")

        # Display options
        options_frame = ttk.LabelFrame(display_frame, text="Display Options", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.show_favicon_var = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame,
            text="Show website favicons",
            variable=self.show_favicon_var,
            command=self._on_setting_changed,
            state='disabled'  # Not implemented yet
        ).pack(anchor=tk.W)

        # Performance settings
        perf_frame = ttk.LabelFrame(display_frame, text="Performance", padding=10)
        perf_frame.pack(fill=tk.X, padx=10, pady=5)

        limit_frame = ttk.Frame(perf_frame)
        limit_frame.pack(fill=tk.X)

        ttk.Label(limit_frame, text="Maximum links to display:").pack(side=tk.LEFT)
        self.max_links_var = tk.IntVar()
        ttk.Spinbox(
            limit_frame,
            from_=100,
            to=10000,
            increment=100,
            textvariable=self.max_links_var,
            width=10,
            command=self._on_setting_changed
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Theme settings
        theme_frame = ttk.LabelFrame(display_frame, text="Theme", padding=10)
        theme_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=['default', 'clam', 'alt', 'classic'],
            state='readonly',
            width=15
        )
        theme_combo.pack(side=tk.LEFT, padx=(5, 0))
        theme_combo.bind('<<ComboboxSelected>>', lambda e: self._on_setting_changed())

    def _load_settings(self):
        """Load current settings into UI."""
        # General settings
        self.auto_scan_var.set(self.settings_manager.get('auto_scan_enabled', True))
        self.scan_interval_var.set(self.settings_manager.get('auto_scan_interval', 60))
        self.start_minimized_var.set(self.settings_manager.get('start_minimized', False))
        self.minimize_to_tray_var.set(self.settings_manager.get('minimize_to_tray', False))
        self.confirm_delete_var.set(self.settings_manager.get('confirm_delete', True))

        # Browser settings
        self.browser_var.set(self.settings_manager.get('default_browser', 'system'))

        # Display settings
        self.show_favicon_var.set(self.settings_manager.get('show_favicon', True))
        self.max_links_var.set(self.settings_manager.get('max_links_display', 1000))
        self.theme_var.set(self.settings_manager.get('theme', 'default'))

    def _save_settings(self):
        """Save current UI values to settings."""
        # General settings
        self.settings_manager.set('auto_scan_enabled', self.auto_scan_var.get())
        self.settings_manager.set('auto_scan_interval', self.scan_interval_var.get())
        self.settings_manager.set('start_minimized', self.start_minimized_var.get())
        self.settings_manager.set('minimize_to_tray', self.minimize_to_tray_var.get())
        self.settings_manager.set('confirm_delete', self.confirm_delete_var.get())

        # Browser settings
        self.settings_manager.set('default_browser', self.browser_var.get())

        # Display settings
        self.settings_manager.set('show_favicon', self.show_favicon_var.get())
        self.settings_manager.set('max_links_display', self.max_links_var.get())
        self.settings_manager.set('theme', self.theme_var.get())

        # Save to file
        self.settings_manager.save()

    def _on_setting_changed(self):
        """Called when any setting is changed."""
        self.changed = True

    def _on_ok(self):
        """Handle OK button click."""
        self._save_settings()
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle Cancel button click."""
        if self.changed:
            if messagebox.askyesno("Unsaved Changes",
                                  "You have unsaved changes. Discard them?"):
                self.dialog.destroy()
        else:
            self.dialog.destroy()

    def _on_apply(self):
        """Handle Apply button click."""
        self._save_settings()
        self.changed = False
        messagebox.showinfo("Settings", "Settings have been applied.")

    def _on_reset(self):
        """Handle Reset to Defaults button click."""
        if messagebox.askyesno("Reset Settings",
                              "Reset all settings to default values?"):
            self.settings_manager.reset()
            self._load_settings()
            self.changed = True