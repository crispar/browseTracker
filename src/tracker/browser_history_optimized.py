"""
Optimized browser history scanner module.
Performance improvements for faster scanning and loading.
"""

import sqlite3
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import logging
from contextlib import contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from tracker.browser_paths import BrowserProfile, BrowserPathFinder

logger = logging.getLogger(__name__)


class OptimizedBrowserHistoryScanner:
    """Optimized scanner with better performance."""

    # Chrome/Edge use Windows epoch (1601-01-01) for timestamps
    CHROME_EPOCH = datetime(1601, 1, 1)

    # Cache for scanned URLs to avoid duplicates
    _url_cache: Set[str] = set()
    _cache_lock = threading.Lock()

    def __init__(self):
        """Initialize the history scanner."""
        self.profiles = []
        # Thread pool for parallel scanning
        self.executor = ThreadPoolExecutor(max_workers=4)

    def discover_browsers(self) -> List[BrowserProfile]:
        """Discover all available browser profiles."""
        self.profiles = BrowserPathFinder.find_browser_profiles()
        return self.profiles

    def scan_browser_profile(self, profile: BrowserProfile,
                           since: Optional[datetime] = None,
                           limit: Optional[int] = 1000) -> List[Dict]:
        """Scan a specific browser profile's history with optimizations.

        Args:
            profile: BrowserProfile object to scan
            since: Only get URLs visited after this time
            limit: Maximum number of results (default 1000 for performance)

        Returns:
            List of dictionaries with URL data
        """
        if not profile.is_valid():
            logger.warning(f"Invalid profile: {profile}")
            return []

        # Copy the database to avoid locking issues
        with self._get_temp_db_copy(profile.history_db_path) as temp_db_path:
            return self._read_history_db_optimized(temp_db_path, profile, since, limit)

    @contextmanager
    def _get_temp_db_copy(self, db_path: Path):
        """Create a temporary copy of the database to avoid lock issues."""
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

    def _read_history_db_optimized(self, db_path: Path, profile: BrowserProfile,
                                  since: Optional[datetime] = None,
                                  limit: Optional[int] = 1000) -> List[Dict]:
        """Optimized database reading with better performance.

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
            # Optimized query - get only essential data
            # Use index on visit_time for faster filtering
            query = """
                SELECT DISTINCT
                    urls.url,
                    urls.title,
                    urls.visit_count,
                    MAX(visits.visit_time) as last_visit_time
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

            # Group by URL for better performance
            query += " GROUP BY urls.url"

            # Order by most recent first
            query += " ORDER BY last_visit_time DESC"

            # Add limit for performance
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries with caching
            results = []
            with self._cache_lock:
                for row in rows:
                    url = row['url']

                    # Skip if already in cache (for current session)
                    if url in self._url_cache:
                        continue

                    self._url_cache.add(url)

                    visited_at = self._chrome_timestamp_to_datetime(row['last_visit_time'])

                    results.append({
                        'url': url,
                        'title': row['title'] or url,
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
        """Convert Chrome timestamp to Python datetime."""
        # Chrome timestamp is in microseconds
        seconds_since_chrome_epoch = chrome_timestamp / 1_000_000
        return self.CHROME_EPOCH + timedelta(seconds=seconds_since_chrome_epoch)

    def _datetime_to_chrome_timestamp(self, dt: datetime) -> int:
        """Convert Python datetime to Chrome timestamp."""
        delta = dt - self.CHROME_EPOCH
        return int(delta.total_seconds() * 1_000_000)

    def scan_all_profiles_parallel(self, since: Optional[datetime] = None,
                                  limit: Optional[int] = 500) -> Dict[str, List[Dict]]:
        """Scan all profiles in parallel for better performance.

        Args:
            since: Only get URLs visited after this time
            limit: Maximum results per browser

        Returns:
            Dictionary mapping profile strings to lists of URL data
        """
        results = {}

        if not self.profiles:
            self.discover_browsers()

        # Submit all scanning tasks to thread pool
        futures = {}
        for profile in self.profiles:
            future = self.executor.submit(
                self.scan_browser_profile,
                profile, since, limit
            )
            futures[future] = profile

        # Collect results as they complete
        for future in as_completed(futures):
            profile = futures[future]
            try:
                history = future.result(timeout=5)  # 5 second timeout per profile
                if history:
                    results[str(profile)] = history
                    logger.info(f"Scanned {len(history)} URLs from {profile}")
            except Exception as e:
                logger.error(f"Error scanning {profile}: {e}")

        return results

    def get_recent_history(self, hours: int = 24,
                          limit: Optional[int] = 100) -> Dict[str, List[Dict]]:
        """Get recent browsing history with optimizations."""
        since = datetime.now() - timedelta(hours=hours)
        return self.scan_all_profiles_parallel(since=since, limit=limit)

    def cleanup(self):
        """Clean up resources."""
        self.executor.shutdown(wait=False)
        with self._cache_lock:
            self._url_cache.clear()


class OptimizedHistoryTracker:
    """Optimized history tracker with batch operations."""

    def __init__(self, db_manager):
        """Initialize the history tracker.

        Args:
            db_manager: DatabaseManager instance for storing links
        """
        self.db_manager = db_manager
        self.scanner = OptimizedBrowserHistoryScanner()
        self.last_scan_time = {}
        self._scan_lock = threading.Lock()

    def initialize(self) -> List[BrowserProfile]:
        """Initialize tracker and discover browsers."""
        profiles = self.scanner.discover_browsers()

        # Register profiles in database
        for profile in profiles:
            self.db_manager.register_browser_source(
                browser_name=profile.browser,
                profile_name=profile.profile_name,
                profile_path=str(profile.profile_path)
            )

        return profiles

    def scan_and_update_batch(self, since_hours: int = 24,
                             max_items: int = 500) -> Dict[str, int]:
        """Scan browser history and update database using batch operations.

        Args:
            since_hours: How many hours back to scan
            max_items: Maximum items to process per profile

        Returns:
            Dictionary with counts of new and updated links per profile
        """
        with self._scan_lock:
            stats = {}
            since = datetime.now() - timedelta(hours=since_hours)

            # Get all browser sources from database
            sources = self.db_manager.get_browser_sources(active_only=True)

            # Process each source
            for source in sources:
                profile_path = Path(source.profile_path)
                profile = BrowserProfile(
                    browser=source.browser_name,
                    profile_name=source.profile_name,
                    profile_path=profile_path
                )

                if not profile.is_valid():
                    continue

                try:
                    # Use last scan time if available, otherwise use since parameter
                    scan_since = source.last_scanned_at or since

                    # Scan with limit for performance
                    history = self.scanner.scan_browser_profile(
                        profile,
                        since=scan_since,
                        limit=max_items
                    )

                    if history:
                        # Batch insert/update for better performance
                        new_count, updated_count = self._batch_update_links(
                            history,
                            source.browser_name,
                            source.profile_name
                        )

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

    def _batch_update_links(self, history_items: List[Dict],
                          browser: str, browser_profile: str) -> tuple:
        """Batch update links for better performance.

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        # Process in smaller batches to avoid memory issues
        batch_size = 50
        for i in range(0, len(history_items), batch_size):
            batch = history_items[i:i + batch_size]

            for item in batch:
                link = self.db_manager.upsert_link(
                    url=item['url'],
                    title=item['title'],
                    browser=browser,
                    browser_profile=browser_profile,
                    visited_at=item.get('visited_at')  # Pass the actual visit time
                )

                if link.access_count == 1:
                    new_count += 1
                else:
                    updated_count += 1

        return new_count, updated_count

    def cleanup(self):
        """Clean up resources."""
        self.scanner.cleanup()