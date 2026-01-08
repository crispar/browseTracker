"""
Application configuration and settings.
"""

import os
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class AppConfig:
    """Application configuration manager."""

    # Default configuration
    DEFAULTS = {
        'scan_interval': 300,  # 5 minutes in seconds
        'auto_scan': True,
        'theme': 'default',
        'window_geometry': '1200x700',
        'show_favicon': True,
        'max_title_length': 80,
        'date_format': '%Y-%m-%d %H:%M',
        'browsers': {
            'Chrome': True,
            'Edge': True,
            'Brave': True,
            'Opera': False,
            'Vivaldi': False
        },
        'columns_visible': {
            'title': True,
            'url': True,
            'categories': True,
            'tags': True,
            'last_accessed': True,
            'access_count': True,
            'browser': False,
            'favorite': True
        },
        'column_widths': {
            'title': 300,
            'url': 300,
            'categories': 150,
            'tags': 150,
            'last_accessed': 150,
            'access_count': 80,
            'browser': 100,
            'favorite': 50
        }
    }

    def __init__(self):
        """Initialize configuration."""
        self.config_path = self._get_config_path()
        self.config = self.load_config()

    def _get_config_path(self) -> Path:
        """Get path to configuration file."""
        if os.environ.get('LINK_TRACKER_DEV'):
            return Path('config.json')
        else:
            app_data = Path(os.environ.get('APPDATA', '.'))
            config_dir = app_data / 'LinkTracker'
            config_dir.mkdir(exist_ok=True)
            return config_dir / 'config.json'

    def load_config(self) -> dict:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle missing keys
                    return self._merge_configs(self.DEFAULTS.copy(), loaded)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading config: {e}")

        # Return defaults if no config or error
        return self.DEFAULTS.copy()

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except IOError as e:
            logger.error(f"Error saving config: {e}")

    def _merge_configs(self, base: dict, override: dict) -> dict:
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._merge_configs(base[key], value)
            else:
                base[key] = value
        return base

    def get(self, key: str, default=None):
        """Get configuration value by key (supports dot notation)."""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value):
        """Set configuration value by key (supports dot notation)."""
        keys = key.split('.')
        config = self.config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value
        self.save_config()

    @property
    def scan_interval(self) -> int:
        """Get scan interval in seconds."""
        return self.config.get('scan_interval', 300)

    @property
    def auto_scan(self) -> bool:
        """Check if auto-scan is enabled."""
        return self.config.get('auto_scan', True)

    @property
    def enabled_browsers(self) -> list:
        """Get list of enabled browsers."""
        browsers = self.config.get('browsers', {})
        return [name for name, enabled in browsers.items() if enabled]


# Global configuration instance
_config = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config