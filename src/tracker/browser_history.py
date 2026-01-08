"""
Browser history scanner module.
Reads Chrome/Edge history databases and extracts visited URLs.
"""

import sqlite3
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from contextlib import contextmanager

from tracker.browser_paths import BrowserProfile, BrowserPathFinder

logger = logging.getLogger(__name__)


class BrowserHistoryScanner:
    """Scans browser history databases for visited URLs."""

    # Chrome/Edge use Windows epoch (1601-01-01) for timestamps
    CHROME_EPOCH = datetime(1601, 1, 1)

    def __init__(self):
        """Initialize the history scanner."""
        self.profiles = []

    def discover_browsers(self) -> List[BrowserProfile]:
        """Discover all available browser profiles."""
        self.profiles = BrowserPathFinder.find_browser_profiles()
        return self.profiles

    def scan_browser_profile(self, profile: BrowserProfile,
                           since: Optional[datetime] = None,
                           limit: Optional[int] = None) -> List[Dict]:
        """Scan a specific browser profile's history.

        Args:
            profile: BrowserProfile object to scan
            since: Only get URLs visited after this time
            limit: Maximum number of results

        Returns:
            List of dictionaries with URL data
        """
        if not profile.is_valid():
            logger.warning(f"Invalid profile: {profile}")
            return []

        # Copy the database to avoid locking issues
        with self._get_temp_db_copy(profile.history_db_path) as temp_db_path:
            return self._read_history_db(temp_db_path, profile, since, limit)

    def scan_all_profiles(self, since: Optional[datetime] = None,
                         limit: Optional[int] = None) -> Dict[str, List[Dict]]:
        """Scan all discovered browser profiles.

        Args:
            since: Only get URLs visited after this time
            limit: Maximum results per browser

        Returns:
            Dictionary mapping profile strings to lists of URL data
        """
        results = {}

        if not self.profiles:
            self.discover_browsers()

        for profile in self.profiles:
            try:
                history = self.scan_browser_profile(profile, since, limit)
                if history:
                    results[str(profile)] = history
                    logger.info(f"Scanned {len(history)} URLs from {profile}")
            except Exception as e:
                logger.error(f"Error scanning {profile}: {e}")

        return results

    @contextmanager
    def _get_temp_db_copy(self, db_path: Path):
        """Create a temporary copy of the database to avoid lock issues.

        Args:
            db_path: Path to the original database

        Yields:
            Path to temporary database copy
        """
        temp_file = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tf:
                temp_file = Path(tf.name)

            # Copy the database
            shutil.copy2(db_path, temp_file)
            yield temp_file

        finally:
            # Clean up temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_file}: {e}")

    def _read_history_db(self, db_path: Path, profile: BrowserProfile,
                        since: Optional[datetime] = None,
                        limit: Optional[int] = None) -> List[Dict]:
        """Read history from a Chrome/Edge SQLite database.

        Args:
            db_path: Path to the database file
            profile: BrowserProfile information
            since: Only get URLs visited after this time
            limit: Maximum number of results

        Returns:
            List of dictionaries with URL data
        """
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Build the query
            query = """
                SELECT
                    urls.url,
                    urls.title,
                    urls.visit_count,
                    visits.visit_time,
                    visits.id as visit_id
                FROM urls
                JOIN visits ON urls.id = visits.url
            """

            params = []

            # Add time filter if specified
            if since:
                # Convert datetime to Chrome timestamp
                chrome_timestamp = self._datetime_to_chrome_timestamp(since)
                query += " WHERE visits.visit_time >= ?"
                params.append(chrome_timestamp)

            # Order by most recent first
            query += " ORDER BY visits.visit_time DESC"

            # Add limit if specified
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = []
            for row in rows:
                visited_at = self._chrome_timestamp_to_datetime(row['visit_time'])

                results.append({
                    'url': row['url'],
                    'title': row['title'] or row['url'],
                    'visit_count': row['visit_count'],
                    'visited_at': visited_at,
                    'browser': profile.browser,
                    'profile': profile.profile_name
                })

            return results

        except sqlite3.Error as e:
            logger.error(f"Error reading history database: {e}")
            return []

        finally:
            conn.close()

    def _chrome_timestamp_to_datetime(self, chrome_timestamp: int) -> datetime:
        """Convert Chrome timestamp to Python datetime.

        Chrome uses microseconds since 1601-01-01.
        """
        # Chrome timestamp is in microseconds
        seconds_since_chrome_epoch = chrome_timestamp / 1_000_000
        return self.CHROME_EPOCH + timedelta(seconds=seconds_since_chrome_epoch)

    def _datetime_to_chrome_timestamp(self, dt: datetime) -> int:
        """Convert Python datetime to Chrome timestamp."""
        delta = dt - self.CHROME_EPOCH
        return int(delta.total_seconds() * 1_000_000)

    def get_recent_history(self, hours: int = 24,
                          limit: Optional[int] = 100) -> Dict[str, List[Dict]]:
        """Get recent browsing history across all browsers.

        Args:
            hours: How many hours back to look
            limit: Maximum results per browser

        Returns:
            Dictionary mapping profile strings to lists of URL data
        """
        since = datetime.now() - timedelta(hours=hours)
        return self.scan_all_profiles(since=since, limit=limit)

    def get_unique_urls(self, since: Optional[datetime] = None) -> Dict[str, Dict]:
        """Get unique URLs across all browsers.

        Returns a dictionary where keys are URLs and values contain
        aggregated information about that URL from all browsers.
        """
        all_history = self.scan_all_profiles(since=since)
        unique_urls = {}

        for profile_name, history_list in all_history.items():
            for item in history_list:
                url = item['url']

                if url not in unique_urls:
                    unique_urls[url] = {
                        'url': url,
                        'title': item['title'],
                        'first_visited': item['visited_at'],
                        'last_visited': item['visited_at'],
                        'total_visits': 0,
                        'browsers': set(),
                        'profiles': set()
                    }

                # Update aggregated data
                unique_urls[url]['total_visits'] += 1
                unique_urls[url]['browsers'].add(item['browser'])
                unique_urls[url]['profiles'].add(f"{item['browser']} - {item['profile']}")

                # Update title if current one is better (longer)
                if len(item['title']) > len(unique_urls[url]['title']):
                    unique_urls[url]['title'] = item['title']

                # Update visit times
                if item['visited_at'] < unique_urls[url]['first_visited']:
                    unique_urls[url]['first_visited'] = item['visited_at']
                if item['visited_at'] > unique_urls[url]['last_visited']:
                    unique_urls[url]['last_visited'] = item['visited_at']

        # Convert sets to lists for JSON serialization
        for url_data in unique_urls.values():
            url_data['browsers'] = list(url_data['browsers'])
            url_data['profiles'] = list(url_data['profiles'])

        return unique_urls


class HistoryTracker:
    """Main class for tracking browser history continuously."""

    def __init__(self, db_manager):
        """Initialize the history tracker.

        Args:
            db_manager: DatabaseManager instance for storing links
        """
        self.db_manager = db_manager
        self.scanner = BrowserHistoryScanner()
        self.last_scan_time = {}  # Track last scan per profile

    def initialize(self) -> List[BrowserProfile]:
        """Initialize tracker and discover browsers.

        Returns:
            List of discovered browser profiles
        """
        profiles = self.scanner.discover_browsers()

        # Register profiles in database
        for profile in profiles:
            self.db_manager.register_browser_source(
                browser_name=profile.browser,
                profile_name=profile.profile_name,
                profile_path=str(profile.profile_path)
            )

        return profiles

    def scan_and_update(self, since_hours: int = 24) -> Dict[str, int]:
        """Scan browser history and update database.

        Args:
            since_hours: How many hours back to scan

        Returns:
            Dictionary with counts of new and updated links per profile
        """
        stats = {}
        since = datetime.now() - timedelta(hours=since_hours)

        # Get all browser sources from database
        sources = self.db_manager.get_browser_sources(active_only=True)

        for source in sources:
            profile_path = Path(source.profile_path)
            profile = BrowserProfile(
                browser=source.browser_name,
                profile_name=source.profile_name,
                profile_path=profile_path
            )

            if not profile.is_valid():
                continue

            # Scan this profile
            try:
                # Use last scan time if available, otherwise use since parameter
                scan_since = source.last_scanned_at or since

                history = self.scanner.scan_browser_profile(profile, since=scan_since)

                new_count = 0
                updated_count = 0

                for item in history:
                    link = self.db_manager.upsert_link(
                        url=item['url'],
                        title=item['title'],
                        browser=item['browser'],
                        browser_profile=item['profile']
                    )

                    if link.access_count == 1:
                        new_count += 1
                    else:
                        updated_count += 1

                # Update scan time
                self.db_manager.update_browser_scan_time(source.id)

                profile_key = f"{source.browser_name} - {source.profile_name}"
                stats[profile_key] = {
                    'new': new_count,
                    'updated': updated_count,
                    'total': len(history)
                }

                logger.info(f"Scanned {profile_key}: {new_count} new, {updated_count} updated")

            except Exception as e:
                logger.error(f"Error scanning {profile}: {e}")
                stats[str(profile)] = {'error': str(e)}

        return stats


if __name__ == "__main__":
    # Test the scanner
    import pprint

    scanner = BrowserHistoryScanner()

    print("Discovering browsers...")
    profiles = scanner.discover_browsers()

    if profiles:
        print(f"\nFound {len(profiles)} browser profiles:")
        for p in profiles:
            print(f"  - {p}")

        print("\n\nScanning recent history (last 24 hours)...")
        recent = scanner.get_recent_history(hours=24, limit=10)

        if recent:
            print("\nRecent browsing history:")
            for profile_name, history in recent.items():
                print(f"\n{profile_name}:")
                for item in history[:5]:  # Show first 5 items
                    print(f"  - {item['title'][:50]}...")
                    print(f"    URL: {item['url'][:80]}...")
                    print(f"    Visited: {item['visited_at']}")
        else:
            print("No recent history found.")
    else:
        print("No browser profiles found.")