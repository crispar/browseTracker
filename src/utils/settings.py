"""Settings manager for Browser Link Tracker."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages application settings with persistence."""

    DEFAULT_SETTINGS = {
        'default_browser': 'system',  # 'system', 'chrome', 'edge', 'firefox', etc.
        'auto_scan_interval': 60,  # seconds
        'auto_scan_enabled': True,
        'minimize_to_tray': False,
        'start_minimized': False,
        'theme': 'default',
        'show_favicon': True,
        'confirm_delete': True,
        'max_links_display': 1000,
    }

    def __init__(self, settings_file: Optional[Path] = None):
        """Initialize settings manager.

        Args:
            settings_file: Path to settings file. If None, uses default location.
        """
        if settings_file is None:
            # Use AppData folder on Windows
            if os.name == 'nt':
                appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                settings_dir = Path(appdata) / 'BrowserLinkTracker'
            else:
                settings_dir = Path.home() / '.browser_link_tracker'

            settings_dir.mkdir(parents=True, exist_ok=True)
            self.settings_file = settings_dir / 'settings.json'
        else:
            self.settings_file = settings_file

        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    return settings
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load settings: {e}")

        return self.DEFAULT_SETTINGS.copy()

    def save(self) -> bool:
        """Save settings to file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Could not save settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value

    def reset(self) -> None:
        """Reset all settings to defaults."""
        self.settings = self.DEFAULT_SETTINGS.copy()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings.

        Returns:
            Dictionary of all settings
        """
        return self.settings.copy()