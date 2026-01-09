"""
Database manager for SQLite operations.
Handles all database interactions with proper error handling and connection management.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import logging

from .models import (
    SCHEMA_SQL,
    Link,
    Category,
    Tag,
    Visit,
    BrowserSource,
    URLFilter
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all database operations for the Link Tracker."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            # Use user's AppData for production, local for development
            if os.environ.get('LINK_TRACKER_DEV'):
                db_path = Path('data/links.db')
            else:
                app_data = Path(os.environ.get('APPDATA', '.'))
                db_dir = app_data / 'LinkTracker'
                db_dir.mkdir(exist_ok=True)
                db_path = db_dir / 'links.db'

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_database()

    def _init_database(self):
        """Create database schema if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # First, check if links table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links'")
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Table exists, perform comprehensive migration
                cursor.execute("PRAGMA table_info(links)")
                columns = [col[1] for col in cursor.fetchall()]
                column_set = set(columns)

                # List of columns that might be missing in old databases
                migrations = [
                    ('normalized_url', "ALTER TABLE links ADD COLUMN normalized_url TEXT"),
                    ('favicon_url', "ALTER TABLE links ADD COLUMN favicon_url TEXT"),
                    ('is_deleted', "ALTER TABLE links ADD COLUMN is_deleted BOOLEAN DEFAULT 0"),
                    ('deleted_at', "ALTER TABLE links ADD COLUMN deleted_at TIMESTAMP"),
                ]

                # Add missing columns
                for col_name, sql in migrations:
                    if col_name not in column_set:
                        logger.info(f"Migrating database: Adding {col_name} column")
                        try:
                            cursor.execute(sql)
                            conn.commit()
                        except sqlite3.OperationalError as e:
                            logger.warning(f"Could not add column {col_name}: {e}")

                # Create other tables if they don't exist
                # (we can't use executescript here due to potential column mismatches)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT DEFAULT '#808080',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_categories (
                    link_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    PRIMARY KEY (link_id, category_id),
                    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_tags (
                    link_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (link_id, tag_id),
                    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER NOT NULL,
                    browser TEXT,
                    browser_profile TEXT,
                    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
                )
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS url_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL UNIQUE,
                    filter_type TEXT NOT NULL DEFAULT 'domain',
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                logger.info("Database migration completed")
            else:
                # No existing table, create everything fresh
                conn.executescript(SCHEMA_SQL)

            # Create indexes for performance (these are idempotent)
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_links_url ON links(url)",
                "CREATE INDEX IF NOT EXISTS idx_links_normalized_url ON links(normalized_url)",
                "CREATE INDEX IF NOT EXISTS idx_links_last_accessed ON links(last_accessed_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_links_access_count ON links(access_count DESC)",
                "CREATE INDEX IF NOT EXISTS idx_links_title ON links(title)",
                "CREATE INDEX IF NOT EXISTS idx_links_is_deleted ON links(is_deleted)",
                "CREATE INDEX IF NOT EXISTS idx_links_deleted_at ON links(deleted_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_links_composite_deleted ON links(is_deleted, deleted_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_visits_link_id ON visits(link_id)",
                "CREATE INDEX IF NOT EXISTS idx_visits_visited_at ON visits(visited_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_filters_active ON url_filters(is_active)",
            ]

            for idx_sql in indexes:
                try:
                    cursor.execute(idx_sql)
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not create index: {e}")

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_columns_exist(self, conn):
        """Ensure is_deleted and deleted_at columns exist (emergency migration)."""
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_deleted FROM links LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            logger.warning("Emergency migration: Adding is_deleted column")
            cursor.execute("ALTER TABLE links ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE links ADD COLUMN deleted_at TIMESTAMP")
            conn.commit()

    # ============ Link Operations ============

    def upsert_link(self, url: str, title: Optional[str] = None,
                    browser: Optional[str] = None,
                    browser_profile: Optional[str] = None,
                    visited_at: Optional[datetime] = None) -> Link:
        """Insert or update a link, incrementing access count.

        Args:
            url: The URL to track
            title: Optional page title
            browser: Browser name (chrome/edge/etc)
            browser_profile: Browser profile name
            visited_at: Actual visit time from browser history

        Returns:
            The created or updated Link object
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if link exists (including deleted ones)
            cursor.execute("SELECT * FROM links WHERE url = ?", (url,))
            existing = cursor.fetchone()

            # Use provided visited_at time, or current time as fallback
            visit_time = visited_at.isoformat() if visited_at else datetime.now().isoformat()
            now = datetime.now().isoformat()

            if existing:
                # Check if link was deleted
                try:
                    is_deleted = existing['is_deleted']
                except (KeyError, IndexError):
                    is_deleted = 0

                # If link is deleted, don't update it - treat as if it doesn't exist
                if is_deleted:
                    logger.info(f"Skipping update for deleted link: {url}")
                    # Return without updating (the link stays deleted)
                    return Link.from_row(existing)

                # Update existing link - only update last_accessed_at if new visit is more recent
                existing_last_accessed = existing['last_accessed_at']
                if not existing_last_accessed or visit_time > existing_last_accessed:
                    cursor.execute("""
                        UPDATE links
                        SET title = COALESCE(?, title),
                            last_accessed_at = ?,
                            access_count = access_count + 1,
                            updated_at = ?
                        WHERE url = ? AND (is_deleted = 0 OR is_deleted IS NULL)
                    """, (title, visit_time, now, url))
                else:
                    # Just update access count if this is an older visit
                    cursor.execute("""
                        UPDATE links
                        SET title = COALESCE(?, title),
                            access_count = access_count + 1,
                            updated_at = ?
                        WHERE url = ? AND (is_deleted = 0 OR is_deleted IS NULL)
                    """, (title, now, url))

                link_id = existing['id']
            else:
                # Insert new link
                cursor.execute("""
                    INSERT INTO links (url, title, created_at, updated_at, last_accessed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (url, title or url, now, now, visit_time))
                link_id = cursor.lastrowid

            # Record visit if browser info provided
            if browser:
                cursor.execute("""
                    INSERT INTO visits (link_id, browser, browser_profile, visited_at)
                    VALUES (?, ?, ?, ?)
                """, (link_id, browser, browser_profile, visit_time))

            conn.commit()

            # Fetch and return the updated link
            cursor.execute("SELECT * FROM links WHERE id = ?", (link_id,))
            row = cursor.fetchone()
            return Link.from_row(row)

    def get_link(self, link_id: int) -> Optional[Link]:
        """Get a single link by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM links WHERE id = ?", (link_id,))
            row = cursor.fetchone()
            if row:
                link = Link.from_row(row)
                # Load categories and tags
                link.categories = self.get_link_categories(link_id)
                link.tags = self.get_link_tags(link_id)
                return link
            return None

    def get_links(self,
                  category_id: Optional[int] = None,
                  search_query: Optional[str] = None,
                  browser: Optional[str] = None,
                  days_back: Optional[int] = None,
                  sort_by: str = 'last_accessed_at',
                  sort_desc: bool = True,
                  limit: Optional[int] = None,
                  offset: int = 0,
                  include_deleted: bool = False) -> List[Link]:
        """Get filtered and sorted links.

        Args:
            category_id: Filter by category
            search_query: Search in URL, title, notes
            browser: Filter by browser
            days_back: Filter by recent days (e.g., 7 for last week)
            sort_by: Column to sort by
            sort_desc: Sort descending if True
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Link objects
        """
        with self.get_connection() as conn:
            # Ensure columns exist before running queries
            self._ensure_columns_exist(conn)

            query = "SELECT DISTINCT l.* FROM links l"
            where_clauses = []
            params = []

            # Join with categories if filtering by category
            if category_id:
                query += " JOIN link_categories lc ON l.id = lc.link_id"
                where_clauses.append("lc.category_id = ?")
                params.append(category_id)

            # Search filter
            if search_query:
                where_clauses.append(
                    "(l.url LIKE ? OR l.title LIKE ? OR l.notes LIKE ?)"
                )
                search_pattern = f"%{search_query}%"
                params.extend([search_pattern, search_pattern, search_pattern])

            # Browser filter (requires join with visits)
            if browser:
                query += " JOIN visits v ON l.id = v.link_id"
                where_clauses.append("v.browser = ?")
                params.append(browser)

            # Time filter
            if days_back:
                where_clauses.append(
                    "l.last_accessed_at >= datetime('now', '-' || ? || ' days')"
                )
                params.append(days_back)

            # Filter deleted links - optimized for index usage
            if not include_deleted:
                where_clauses.append("(l.is_deleted = 0 OR l.is_deleted IS NULL)")
            elif include_deleted == 'only':  # Special case for trash view
                where_clauses.append("l.is_deleted = 1")

            # Build WHERE clause
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            # Sorting
            valid_sorts = ['last_accessed_at', 'access_count', 'created_at', 'title']
            if sort_by in valid_sorts:
                query += f" ORDER BY l.{sort_by}"
                query += " DESC" if sort_desc else " ASC"

            # Pagination
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            cursor = conn.cursor()
            cursor.execute(query, params)

            links = []
            for row in cursor.fetchall():
                link = Link.from_row(row)
                # Load categories and tags
                link.categories = self.get_link_categories(link.id)
                link.tags = self.get_link_tags(link.id)
                links.append(link)

            return links

    def update_link(self, link_id: int, title: Optional[str] = None,
                   notes: Optional[str] = None, is_favorite: Optional[bool] = None) -> bool:
        """Update link properties."""
        with self.get_connection() as conn:
            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)
            if is_favorite is not None:
                updates.append("is_favorite = ?")
                params.append(int(is_favorite))

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(link_id)

            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE links SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_links_batch(self, link_ids: List[int], permanent: bool = False) -> int:
        """Batch delete multiple links efficiently in a single transaction.

        Args:
            link_ids: List of link IDs to delete
            permanent: If True, permanently delete. If False, soft delete.

        Returns:
            Number of links successfully deleted
        """
        if not link_ids:
            return 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if permanent:
                # Permanent deletion
                placeholders = ','.join('?' * len(link_ids))
                cursor.execute(f"DELETE FROM links WHERE id IN ({placeholders})", link_ids)
            else:
                # Soft delete - batch update
                now = datetime.now().isoformat()
                placeholders = ','.join('?' * len(link_ids))
                cursor.execute(f"""
                    UPDATE links
                    SET is_deleted = 1,
                        deleted_at = ?,
                        updated_at = ?
                    WHERE id IN ({placeholders}) AND (is_deleted = 0 OR is_deleted IS NULL)
                """, [now, now] + link_ids)

            conn.commit()
            return cursor.rowcount

    def delete_link(self, link_id: int, permanent: bool = False) -> bool:
        """Soft delete a link (or permanently delete if specified).

        Args:
            link_id: The link ID to delete
            permanent: If True, permanently delete. If False, soft delete.

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if permanent:
                # Permanent deletion
                cursor.execute("DELETE FROM links WHERE id = ?", (link_id,))
            else:
                # Soft delete - just mark as deleted
                cursor.execute("""
                    UPDATE links
                    SET is_deleted = 1,
                        deleted_at = ?,
                        updated_at = ?
                    WHERE id = ? AND is_deleted = 0
                """, (datetime.now().isoformat(), datetime.now().isoformat(), link_id))

            conn.commit()
            return cursor.rowcount > 0

    def restore_links_batch(self, link_ids: List[int]) -> int:
        """Batch restore multiple soft-deleted links efficiently.

        Args:
            link_ids: List of link IDs to restore

        Returns:
            Number of links successfully restored
        """
        if not link_ids:
            return 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(link_ids))
            cursor.execute(f"""
                UPDATE links
                SET is_deleted = 0,
                    deleted_at = NULL,
                    updated_at = ?
                WHERE id IN ({placeholders}) AND is_deleted = 1
            """, [datetime.now().isoformat()] + link_ids)
            conn.commit()

            restored_count = cursor.rowcount
            if restored_count > 0:
                logger.info(f"Restored {restored_count} links in batch")
            return restored_count

    def restore_link(self, link_id: int) -> bool:
        """Restore a soft-deleted link.

        Args:
            link_id: The link ID to restore

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE links
                SET is_deleted = 0,
                    deleted_at = NULL,
                    updated_at = ?
                WHERE id = ? AND is_deleted = 1
            """, (datetime.now().isoformat(), link_id))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Restored link with ID: {link_id}")
                return True
            return False

    def toggle_favorite(self, link_id: int) -> bool:
        """Toggle the favorite status of a link."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE links
                SET is_favorite = NOT is_favorite,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), link_id))
            conn.commit()
            return cursor.rowcount > 0

    # ============ Category Operations ============

    def create_category(self, name: str, color: str = "#808080",
                       parent_id: Optional[int] = None) -> Category:
        """Create a new category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, color, parent_id)
                VALUES (?, ?, ?)
            """, (name, color, parent_id))
            conn.commit()

            cursor.execute("SELECT * FROM categories WHERE id = ?",
                         (cursor.lastrowid,))
            return Category.from_row(cursor.fetchone())

    def get_categories(self) -> List[Category]:
        """Get all categories, organized hierarchically."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM categories
                ORDER BY parent_id, sort_order, name
            """)

            categories = []
            category_map = {}

            for row in cursor.fetchall():
                category = Category.from_row(row)
                category_map[category.id] = category

                if category.parent_id:
                    parent = category_map.get(category.parent_id)
                    if parent:
                        parent.children.append(category)
                else:
                    categories.append(category)

            return categories

    def update_category(self, category_id: int, name: Optional[str] = None,
                       color: Optional[str] = None) -> bool:
        """Update category properties."""
        with self.get_connection() as conn:
            updates = []
            params = []

            if name:
                updates.append("name = ?")
                params.append(name)
            if color:
                updates.append("color = ?")
                params.append(color)

            if not updates:
                return False

            params.append(category_id)
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_category(self, category_id: int) -> bool:
        """Delete a category and all associations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_link_to_category(self, link_id: int, category_id: int) -> bool:
        """Associate a link with a category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO link_categories (link_id, category_id)
                    VALUES (?, ?)
                """, (link_id, category_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Already exists
                return False

    def remove_link_from_category(self, link_id: int, category_id: int) -> bool:
        """Remove link-category association."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM link_categories
                WHERE link_id = ? AND category_id = ?
            """, (link_id, category_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_link_categories(self, link_id: int) -> List[Category]:
        """Get all categories for a link."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.* FROM categories c
                JOIN link_categories lc ON c.id = lc.category_id
                WHERE lc.link_id = ?
                ORDER BY c.name
            """, (link_id,))

            return [Category.from_row(row) for row in cursor.fetchall()]

    # ============ Tag Operations ============

    def create_tag(self, name: str) -> Tag:
        """Create or get existing tag."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if exists
            cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
            existing = cursor.fetchone()
            if existing:
                return Tag.from_row(existing)

            # Create new
            cursor.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            conn.commit()

            cursor.execute("SELECT * FROM tags WHERE id = ?",
                         (cursor.lastrowid,))
            return Tag.from_row(cursor.fetchone())

    def get_tags(self) -> List[Tag]:
        """Get all tags."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags ORDER BY name")
            return [Tag.from_row(row) for row in cursor.fetchall()]

    def add_tag_to_link(self, link_id: int, tag_name: str) -> bool:
        """Add a tag to a link (creates tag if needed)."""
        tag = self.create_tag(tag_name)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO link_tags (link_id, tag_id)
                    VALUES (?, ?)
                """, (link_id, tag.id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_tag_from_link(self, link_id: int, tag_id: int) -> bool:
        """Remove a tag from a link."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM link_tags
                WHERE link_id = ? AND tag_id = ?
            """, (link_id, tag_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_link_tags(self, link_id: int) -> List[Tag]:
        """Get all tags for a link."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = ?
                ORDER BY t.name
            """, (link_id,))

            return [Tag.from_row(row) for row in cursor.fetchall()]

    # ============ Browser Source Operations ============

    def register_browser_source(self, browser_name: str, profile_name: str,
                               profile_path: str) -> BrowserSource:
        """Register a browser profile for tracking."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if exists
            cursor.execute("""
                SELECT * FROM browser_sources
                WHERE browser_name = ? AND profile_name = ?
            """, (browser_name, profile_name))
            existing = cursor.fetchone()

            if existing:
                # Update path if changed
                cursor.execute("""
                    UPDATE browser_sources
                    SET profile_path = ?
                    WHERE id = ?
                """, (profile_path, existing['id']))
                conn.commit()
                return BrowserSource.from_row(existing)

            # Create new
            cursor.execute("""
                INSERT INTO browser_sources (browser_name, profile_name, profile_path)
                VALUES (?, ?, ?)
            """, (browser_name, profile_name, profile_path))
            conn.commit()

            cursor.execute("SELECT * FROM browser_sources WHERE id = ?",
                         (cursor.lastrowid,))
            return BrowserSource.from_row(cursor.fetchone())

    def get_browser_sources(self, active_only: bool = True) -> List[BrowserSource]:
        """Get registered browser sources."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM browser_sources"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY browser_name, profile_name"

            cursor.execute(query)
            return [BrowserSource.from_row(row) for row in cursor.fetchall()]

    def update_browser_scan_time(self, source_id: int):
        """Update last scan timestamp for a browser source."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE browser_sources
                SET last_scanned_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), source_id))
            conn.commit()

    # ============ Statistics ============

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Link counts
            cursor.execute("SELECT COUNT(*) FROM links")
            stats['total_links'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM links WHERE is_favorite = 1")
            stats['favorite_links'] = cursor.fetchone()[0]

            # Category and tag counts
            cursor.execute("SELECT COUNT(*) FROM categories")
            stats['total_categories'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tags")
            stats['total_tags'] = cursor.fetchone()[0]

            # Visit count
            cursor.execute("SELECT COUNT(*) FROM visits")
            stats['total_visits'] = cursor.fetchone()[0]

            # Top domains
            cursor.execute("""
                SELECT
                    SUBSTR(url,
                           INSTR(url, '://') + 3,
                           INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1) as domain,
                    COUNT(*) as count
                FROM links
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10
            """)
            stats['top_domains'] = [
                {'domain': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]

            return stats

    # ============ Export/Import ============

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all data to a dictionary."""
        links = self.get_links(limit=None, include_deleted=False)  # Don't export deleted links
        categories = self.get_categories()
        tags = self.get_tags()

        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'links': [link.to_dict() for link in links],
            'categories': [
                {
                    'name': cat.name,
                    'color': cat.color,
                    'parent': None  # TODO: Handle hierarchy in export
                }
                for cat in categories
            ],
            'tags': [tag.name for tag in tags]
        }

    def import_from_dict(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Import data from a dictionary.

        Args:
            data: Dictionary containing exported data

        Returns:
            Statistics about the import (new/updated/skipped counts)
        """
        stats = {
            'links_new': 0,
            'links_updated': 0,
            'links_skipped': 0,
            'categories_new': 0,
            'categories_existing': 0,
            'tags_new': 0,
            'tags_existing': 0
        }

        # Import categories first
        if 'categories' in data:
            for cat_data in data['categories']:
                try:
                    self.create_category(
                        name=cat_data['name'],
                        color=cat_data.get('color', '#808080')
                    )
                    stats['categories_new'] += 1
                except sqlite3.IntegrityError:
                    # Category already exists
                    stats['categories_existing'] += 1

        # Import tags
        if 'tags' in data:
            for tag_name in data['tags']:
                try:
                    self.create_tag(tag_name)
                    stats['tags_new'] += 1
                except sqlite3.IntegrityError:
                    # Tag already exists
                    stats['tags_existing'] += 1

        # Import links
        if 'links' in data:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                for link_data in data['links']:
                    url = link_data.get('url')
                    if not url:
                        continue

                    # Check if link exists (including deleted ones)
                    cursor.execute("SELECT * FROM links WHERE url = ?", (url,))
                    existing = cursor.fetchone()

                    if existing:
                        # Check if the existing link is deleted
                        try:
                            is_deleted = existing['is_deleted']
                        except (KeyError, IndexError):
                            is_deleted = 0

                        if is_deleted:
                            # Skip deleted links - don't resurrect them
                            stats['links_skipped'] += 1
                            logger.info(f"Skipping import of deleted link: {url}")
                            continue

                        # Update existing link - merge data
                        # Keep the higher access count
                        new_count = link_data.get('access_count', 1)
                        old_count = existing['access_count'] or 0
                        merged_count = max(new_count, old_count) + 1  # Add 1 for the import action

                        # Keep the most recent access time
                        import_last_accessed = link_data.get('last_accessed_at')
                        existing_last_accessed = existing['last_accessed_at']

                        if import_last_accessed and existing_last_accessed:
                            last_accessed = max(import_last_accessed, existing_last_accessed)
                        else:
                            last_accessed = import_last_accessed or existing_last_accessed

                        cursor.execute("""
                            UPDATE links
                            SET title = COALESCE(?, title),
                                notes = COALESCE(?, notes),
                                is_favorite = COALESCE(?, is_favorite),
                                access_count = ?,
                                last_accessed_at = ?,
                                updated_at = ?
                            WHERE url = ?
                        """, (
                            link_data.get('title'),
                            link_data.get('notes'),
                            link_data.get('is_favorite'),
                            merged_count,
                            last_accessed,
                            datetime.now().isoformat(),
                            url
                        ))
                        stats['links_updated'] += 1
                        link_id = existing['id']
                    else:
                        # Insert new link
                        cursor.execute("""
                            INSERT INTO links (url, title, notes, is_favorite,
                                             created_at, updated_at, last_accessed_at,
                                             access_count, normalized_url, favicon_url)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            url,
                            link_data.get('title', url),
                            link_data.get('notes'),
                            link_data.get('is_favorite', False),
                            link_data.get('created_at', datetime.now().isoformat()),
                            datetime.now().isoformat(),
                            link_data.get('last_accessed_at', datetime.now().isoformat()),
                            link_data.get('access_count', 1),
                            link_data.get('normalized_url'),
                            link_data.get('favicon_url')
                        ))
                        stats['links_new'] += 1
                        link_id = cursor.lastrowid

                    # Import categories for this link
                    if 'categories' in link_data and link_data['categories']:
                        for cat_name in link_data['categories']:
                            cursor.execute("SELECT id FROM categories WHERE name = ?", (cat_name,))
                            cat = cursor.fetchone()
                            if cat:
                                try:
                                    cursor.execute("""
                                        INSERT INTO link_categories (link_id, category_id)
                                        VALUES (?, ?)
                                    """, (link_id, cat['id']))
                                except sqlite3.IntegrityError:
                                    pass  # Link-category association already exists

                    # Import tags for this link
                    if 'tags' in link_data and link_data['tags']:
                        for tag_name in link_data['tags']:
                            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                            tag = cursor.fetchone()
                            if tag:
                                try:
                                    cursor.execute("""
                                        INSERT INTO link_tags (link_id, tag_id)
                                        VALUES (?, ?)
                                    """, (link_id, tag['id']))
                                except sqlite3.IntegrityError:
                                    pass  # Link-tag association already exists

                conn.commit()

        return stats

    # ============ URL Filter Operations ============

    def create_filter(self, pattern: str, filter_type: str = 'domain',
                     description: Optional[str] = None, is_active: bool = True) -> URLFilter:
        """Create a new URL filter.

        Args:
            pattern: The pattern to match (e.g., 'sts.secosso.net')
            filter_type: Type of filter ('domain', 'prefix', 'contains', 'regex')
            description: Optional description of the filter
            is_active: Whether the filter is active

        Returns:
            Created URLFilter object
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO url_filters (pattern, filter_type, description, is_active,
                                       created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pattern, filter_type, description, is_active, now, now))

            conn.commit()
            filter_id = cursor.lastrowid

            # Fetch and return the created filter
            cursor.execute("SELECT * FROM url_filters WHERE id = ?", (filter_id,))
            return URLFilter.from_row(cursor.fetchone())

    def get_filters(self, active_only: bool = True) -> List[URLFilter]:
        """Get all URL filters.

        Args:
            active_only: If True, only return active filters

        Returns:
            List of URLFilter objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute("SELECT * FROM url_filters WHERE is_active = 1 ORDER BY pattern")
            else:
                cursor.execute("SELECT * FROM url_filters ORDER BY pattern")

            return [URLFilter.from_row(row) for row in cursor.fetchall()]

    def update_filter(self, filter_id: int, pattern: Optional[str] = None,
                     filter_type: Optional[str] = None,
                     description: Optional[str] = None,
                     is_active: Optional[bool] = None) -> bool:
        """Update a URL filter.

        Args:
            filter_id: ID of the filter to update
            pattern: New pattern (if provided)
            filter_type: New filter type (if provided)
            description: New description (if provided)
            is_active: New active status (if provided)

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = []
            params = []

            if pattern is not None:
                updates.append("pattern = ?")
                params.append(pattern)
            if filter_type is not None:
                updates.append("filter_type = ?")
                params.append(filter_type)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)

            if not updates:
                return False

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(filter_id)

            query = f"UPDATE url_filters SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0

    def delete_filter(self, filter_id: int) -> bool:
        """Delete a URL filter.

        Args:
            filter_id: ID of the filter to delete

        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM url_filters WHERE id = ?", (filter_id,))
            conn.commit()
            return cursor.rowcount > 0

    def should_track_url(self, url: str) -> bool:
        """Check if a URL should be tracked (not filtered out).

        Args:
            url: The URL to check

        Returns:
            True if the URL should be tracked, False if it should be filtered out
        """
        # Get active filters
        filters = self.get_filters(active_only=True)

        # Check if URL matches any filter
        for url_filter in filters:
            if url_filter.matches(url):
                logger.debug(f"URL {url} filtered by pattern: {url_filter.pattern}")
                return False  # URL is filtered, don't track

        return True  # URL is not filtered, track it

    def close(self):
        """Close database connection (if needed for cleanup)."""
        pass  # SQLite connections are closed in context manager