"""Browser utility functions for Browser Link Tracker."""

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser detection and URL opening."""

    # Common browser configurations
    BROWSERS = {
        'chrome': {
            'names': ['Google Chrome', 'Chrome'],
            'windows_paths': [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
            ],
            'mac_paths': ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
            'linux_commands': ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium'],
        },
        'edge': {
            'names': ['Microsoft Edge', 'Edge'],
            'windows_paths': [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
                os.path.expandvars(r'%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe'),
            ],
            'mac_paths': ['/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'],
            'linux_commands': ['microsoft-edge', 'microsoft-edge-stable', 'microsoft-edge-dev'],
        },
        'firefox': {
            'names': ['Mozilla Firefox', 'Firefox'],
            'windows_paths': [
                r'C:\Program Files\Mozilla Firefox\firefox.exe',
                r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe',
            ],
            'mac_paths': ['/Applications/Firefox.app/Contents/MacOS/firefox'],
            'linux_commands': ['firefox'],
        },
        'brave': {
            'names': ['Brave Browser', 'Brave'],
            'windows_paths': [
                r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
                r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
                os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe'),
            ],
            'mac_paths': ['/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'],
            'linux_commands': ['brave-browser', 'brave'],
        },
        'opera': {
            'names': ['Opera', 'Opera Browser'],
            'windows_paths': [
                r'C:\Program Files\Opera\launcher.exe',
                r'C:\Program Files (x86)\Opera\launcher.exe',
                os.path.expandvars(r'%LOCALAPPDATA%\Programs\Opera\launcher.exe'),
            ],
            'mac_paths': ['/Applications/Opera.app/Contents/MacOS/Opera'],
            'linux_commands': ['opera'],
        },
    }

    def __init__(self):
        """Initialize browser manager."""
        self._detected_browsers = None

    def detect_installed_browsers(self) -> Dict[str, str]:
        """Detect installed browsers on the system.

        Returns:
            Dictionary mapping browser ID to display name and executable path
        """
        if self._detected_browsers is not None:
            return self._detected_browsers

        browsers = {}
        system = os.name

        for browser_id, config in self.BROWSERS.items():
            executable = self._find_browser_executable(browser_id, config, system)
            if executable:
                display_name = config['names'][0]
                browsers[browser_id] = {
                    'name': display_name,
                    'path': executable
                }
                logger.info(f"Detected {display_name} at {executable}")

        # Always include system default
        browsers['system'] = {
            'name': 'System Default Browser',
            'path': None
        }

        self._detected_browsers = browsers
        return browsers

    def _find_browser_executable(self, browser_id: str, config: Dict, system: str) -> Optional[str]:
        """Find browser executable path.

        Args:
            browser_id: Browser identifier
            config: Browser configuration
            system: Operating system ('nt' for Windows)

        Returns:
            Path to browser executable or None
        """
        if system == 'nt':  # Windows
            for path_template in config.get('windows_paths', []):
                path = os.path.expandvars(path_template)
                if os.path.isfile(path):
                    return path
        elif system == 'posix':
            # Try Mac paths
            for path in config.get('mac_paths', []):
                if os.path.isfile(path):
                    return path
            # Try Linux commands
            for command in config.get('linux_commands', []):
                if self._command_exists(command):
                    return command

        return None

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH.

        Args:
            command: Command to check

        Returns:
            True if command exists
        """
        try:
            subprocess.run(['which', command], check=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def open_url(self, url: str, browser_id: str = 'system') -> bool:
        """Open URL in specified browser.

        Args:
            url: URL to open
            browser_id: Browser identifier ('system', 'chrome', 'edge', etc.)

        Returns:
            True if successful
        """
        try:
            if browser_id == 'system' or browser_id not in self.detect_installed_browsers():
                # Use system default
                webbrowser.open(url)
                return True

            browser_info = self.detect_installed_browsers().get(browser_id)
            if not browser_info or not browser_info['path']:
                # Fallback to system default
                webbrowser.open(url)
                return True

            executable = browser_info['path']

            if os.name == 'nt':  # Windows
                subprocess.Popen([executable, url])
            else:  # Mac/Linux
                subprocess.Popen([executable, url])

            logger.info(f"Opened {url} in {browser_info['name']}")
            return True

        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            # Fallback to system default
            try:
                webbrowser.open(url)
                return True
            except:
                return False

    def get_browser_list(self) -> List[Tuple[str, str]]:
        """Get list of available browsers for UI.

        Returns:
            List of (browser_id, display_name) tuples
        """
        browsers = self.detect_installed_browsers()
        result = [('system', 'System Default Browser')]

        for browser_id, info in browsers.items():
            if browser_id != 'system':
                result.append((browser_id, info['name']))

        return result