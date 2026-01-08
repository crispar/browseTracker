"""
Browser profile detection and path utilities.
Finds Chrome/Edge profile locations on Windows.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class BrowserProfile:
    """Represents a browser profile with its path and metadata."""

    def __init__(self, browser: str, profile_name: str, profile_path: Path,
                 is_default: bool = False):
        self.browser = browser
        self.profile_name = profile_name
        self.profile_path = profile_path
        self.is_default = is_default
        self.history_db_path = profile_path / "History"

    def __str__(self):
        return f"{self.browser} - {self.profile_name}"

    def is_valid(self) -> bool:
        """Check if the profile has a valid History database."""
        return self.history_db_path.exists()


class BrowserPathFinder:
    """Finds browser profile paths on the system."""

    # Default paths for browser data on Windows
    BROWSER_PATHS = {
        'Chrome': [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data',
            Path(os.environ.get('APPDATA', '')) / 'Google' / 'Chrome' / 'User Data',
        ],
        'Edge': [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Edge' / 'User Data',
            Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Edge' / 'User Data',
        ],
        'Brave': [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'BraveSoftware' / 'Brave-Browser' / 'User Data',
            Path(os.environ.get('APPDATA', '')) / 'BraveSoftware' / 'Brave-Browser' / 'User Data',
        ],
        'Opera': [
            Path(os.environ.get('APPDATA', '')) / 'Opera Software' / 'Opera Stable',
            Path(os.environ.get('APPDATA', '')) / 'Opera Software' / 'Opera GX Stable',
        ],
        'Vivaldi': [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Vivaldi' / 'User Data',
            Path(os.environ.get('APPDATA', '')) / 'Vivaldi' / 'User Data',
        ]
    }

    @classmethod
    def find_browser_profiles(cls, browser_name: Optional[str] = None) -> List[BrowserProfile]:
        """Find all browser profiles on the system.

        Args:
            browser_name: Specific browser to search for, or None for all

        Returns:
            List of BrowserProfile objects
        """
        profiles = []
        browsers_to_check = {}

        if browser_name:
            if browser_name in cls.BROWSER_PATHS:
                browsers_to_check = {browser_name: cls.BROWSER_PATHS[browser_name]}
        else:
            browsers_to_check = cls.BROWSER_PATHS

        for browser, paths in browsers_to_check.items():
            for base_path in paths:
                if not base_path.exists():
                    continue

                # Find profiles in this browser's data directory
                found_profiles = cls._find_profiles_in_directory(browser, base_path)
                profiles.extend(found_profiles)
                if found_profiles:
                    break  # Found profiles for this browser, skip other paths

        return profiles

    @classmethod
    def _find_profiles_in_directory(cls, browser: str, user_data_path: Path) -> List[BrowserProfile]:
        """Find all profiles in a browser's user data directory."""
        profiles = []

        if not user_data_path.exists():
            return profiles

        # Read the Local State file to get profile info
        local_state_path = user_data_path / "Local State"
        profile_info = {}

        if local_state_path.exists():
            try:
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    if 'profile' in local_state and 'info_cache' in local_state['profile']:
                        profile_info = local_state['profile']['info_cache']
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read Local State file: {e}")

        # Check Default profile
        default_profile_path = user_data_path / "Default"
        if default_profile_path.exists():
            profile_name = profile_info.get('Default', {}).get('name', 'Default')
            profiles.append(BrowserProfile(
                browser=browser,
                profile_name=profile_name,
                profile_path=default_profile_path,
                is_default=True
            ))

        # Check numbered profiles (Profile 1, Profile 2, etc.)
        for profile_dir in user_data_path.glob("Profile *"):
            if profile_dir.is_dir():
                profile_key = profile_dir.name
                profile_display_name = profile_info.get(profile_key, {}).get('name', profile_key)
                profiles.append(BrowserProfile(
                    browser=browser,
                    profile_name=profile_display_name,
                    profile_path=profile_dir,
                    is_default=False
                ))

        # For Opera and some other browsers, the main directory itself might be the profile
        if not profiles and browser in ['Opera']:
            history_path = user_data_path / "History"
            if history_path.exists():
                profiles.append(BrowserProfile(
                    browser=browser,
                    profile_name="Default",
                    profile_path=user_data_path,
                    is_default=True
                ))

        # Filter out invalid profiles
        valid_profiles = [p for p in profiles if p.is_valid()]

        if valid_profiles:
            logger.info(f"Found {len(valid_profiles)} profiles for {browser} in {user_data_path}")

        return valid_profiles

    @classmethod
    def get_default_profiles(cls) -> List[BrowserProfile]:
        """Get only the default profiles for each browser."""
        all_profiles = cls.find_browser_profiles()
        defaults = {}

        for profile in all_profiles:
            if profile.is_default or profile.browser not in defaults:
                defaults[profile.browser] = profile

        return list(defaults.values())


def get_browser_history_path(browser: str, profile_name: str = "Default") -> Optional[Path]:
    """Get the path to a specific browser profile's History database.

    Args:
        browser: Browser name (Chrome, Edge, etc.)
        profile_name: Profile name (Default, Profile 1, etc.)

    Returns:
        Path to History database or None if not found
    """
    profiles = BrowserPathFinder.find_browser_profiles(browser)

    for profile in profiles:
        if profile.profile_name == profile_name:
            if profile.history_db_path.exists():
                return profile.history_db_path

    return None


def list_available_browsers() -> Dict[str, List[str]]:
    """List all available browsers and their profiles.

    Returns:
        Dictionary mapping browser names to lists of profile names
    """
    profiles = BrowserPathFinder.find_browser_profiles()
    result = {}

    for profile in profiles:
        if profile.browser not in result:
            result[profile.browser] = []
        result[profile.browser].append(profile.profile_name)

    return result


if __name__ == "__main__":
    # Test browser detection
    import pprint

    print("Detecting browser profiles...")
    browsers = list_available_browsers()

    if browsers:
        print("\nFound browsers and profiles:")
        pprint.pprint(browsers)

        print("\nProfile details:")
        for profile in BrowserPathFinder.find_browser_profiles():
            print(f"  {profile}")
            print(f"    Path: {profile.profile_path}")
            print(f"    History DB: {profile.history_db_path}")
            print(f"    Valid: {profile.is_valid()}")
    else:
        print("No browser profiles found.")