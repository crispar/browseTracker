"""
Database models and schema definitions for the Browser Link Tracker.
Using raw SQLite for minimal dependencies.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

# SQL schema definitions
SCHEMA_SQL = """
-- Links table: Core URL storage
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    normalized_url TEXT,
    title TEXT,
    favicon_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    notes TEXT,
    is_favorite BOOLEAN DEFAULT 0,
    is_deleted BOOLEAN DEFAULT 0,
    deleted_at TIMESTAMP
);

-- Categories table: Hierarchical organization
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#808080',
    sort_order INTEGER DEFAULT 0,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Link-Category junction table (many-to-many)
CREATE TABLE IF NOT EXISTS link_categories (
    link_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (link_id, category_id),
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Tags table: Flexible labeling
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link-Tag junction table (many-to-many)
CREATE TABLE IF NOT EXISTS link_tags (
    link_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (link_id, tag_id),
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Visits table: Detailed access history (optional for MVP)
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    browser TEXT,
    browser_profile TEXT,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
);

-- Browser sources table: Track which browsers we're monitoring
CREATE TABLE IF NOT EXISTS browser_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    browser_name TEXT NOT NULL,
    profile_name TEXT NOT NULL,
    profile_path TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    last_scanned_at TIMESTAMP,
    UNIQUE(browser_name, profile_name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);
CREATE INDEX IF NOT EXISTS idx_links_normalized_url ON links(normalized_url);
CREATE INDEX IF NOT EXISTS idx_links_last_accessed ON links(last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_links_access_count ON links(access_count DESC);
CREATE INDEX IF NOT EXISTS idx_links_title ON links(title);
CREATE INDEX IF NOT EXISTS idx_visits_link_id ON visits(link_id);
CREATE INDEX IF NOT EXISTS idx_visits_visited_at ON visits(visited_at DESC);
"""


class Link:
    """Represents a tracked link/URL."""

    def __init__(self,
                 id: Optional[int] = None,
                 url: str = "",
                 normalized_url: Optional[str] = None,
                 title: Optional[str] = None,
                 favicon_url: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 last_accessed_at: Optional[datetime] = None,
                 access_count: int = 1,
                 notes: Optional[str] = None,
                 is_favorite: bool = False,
                 is_deleted: bool = False,
                 deleted_at: Optional[datetime] = None):
        self.id = id
        self.url = url
        self.normalized_url = normalized_url
        self.title = title or url
        self.favicon_url = favicon_url
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.last_accessed_at = last_accessed_at or datetime.now()
        self.access_count = access_count
        self.notes = notes
        self.is_favorite = is_favorite
        self.is_deleted = is_deleted
        self.deleted_at = deleted_at
        self.categories: List[Category] = []
        self.tags: List[Tag] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            'id': self.id,
            'url': self.url,
            'normalized_url': self.normalized_url,
            'title': self.title,
            'favicon_url': self.favicon_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'access_count': self.access_count,
            'notes': self.notes,
            'is_favorite': self.is_favorite,
            'categories': [cat.name for cat in self.categories],
            'tags': [tag.name for tag in self.tags]
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Link':
        """Create Link instance from database row."""
        # Handle is_deleted column that may not exist in older databases
        try:
            is_deleted = bool(row['is_deleted'])
        except (KeyError, IndexError):
            is_deleted = False

        try:
            deleted_at = datetime.fromisoformat(row['deleted_at']) if row['deleted_at'] else None
        except (KeyError, IndexError):
            deleted_at = None

        return cls(
            id=row['id'],
            url=row['url'],
            normalized_url=row['normalized_url'],
            title=row['title'],
            favicon_url=row['favicon_url'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            last_accessed_at=datetime.fromisoformat(row['last_accessed_at']) if row['last_accessed_at'] else None,
            access_count=row['access_count'],
            notes=row['notes'],
            is_favorite=bool(row['is_favorite']),
            is_deleted=is_deleted,
            deleted_at=deleted_at
        )


class Category:
    """Represents a category for organizing links."""

    def __init__(self,
                 id: Optional[int] = None,
                 name: str = "",
                 color: str = "#808080",
                 sort_order: int = 0,
                 parent_id: Optional[int] = None):
        self.id = id
        self.name = name
        self.color = color
        self.sort_order = sort_order
        self.parent_id = parent_id
        self.children: List[Category] = []

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Category':
        """Create Category instance from database row."""
        return cls(
            id=row['id'],
            name=row['name'],
            color=row['color'],
            sort_order=row['sort_order'],
            parent_id=row['parent_id']
        )


class Tag:
    """Represents a tag for labeling links."""

    def __init__(self,
                 id: Optional[int] = None,
                 name: str = ""):
        self.id = id
        self.name = name

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Tag':
        """Create Tag instance from database row."""
        return cls(
            id=row['id'],
            name=row['name']
        )


class Visit:
    """Represents a single visit to a link."""

    def __init__(self,
                 id: Optional[int] = None,
                 link_id: int = 0,
                 browser: Optional[str] = None,
                 browser_profile: Optional[str] = None,
                 visited_at: Optional[datetime] = None):
        self.id = id
        self.link_id = link_id
        self.browser = browser
        self.browser_profile = browser_profile
        self.visited_at = visited_at or datetime.now()

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Visit':
        """Create Visit instance from database row."""
        return cls(
            id=row['id'],
            link_id=row['link_id'],
            browser=row['browser'],
            browser_profile=row['browser_profile'],
            visited_at=datetime.fromisoformat(row['visited_at']) if row['visited_at'] else None
        )


class BrowserSource:
    """Represents a browser profile being monitored."""

    def __init__(self,
                 id: Optional[int] = None,
                 browser_name: str = "",
                 profile_name: str = "",
                 profile_path: str = "",
                 is_active: bool = True,
                 last_scanned_at: Optional[datetime] = None):
        self.id = id
        self.browser_name = browser_name
        self.profile_name = profile_name
        self.profile_path = profile_path
        self.is_active = is_active
        self.last_scanned_at = last_scanned_at

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'BrowserSource':
        """Create BrowserSource instance from database row."""
        return cls(
            id=row['id'],
            browser_name=row['browser_name'],
            profile_name=row['profile_name'],
            profile_path=row['profile_path'],
            is_active=bool(row['is_active']),
            last_scanned_at=datetime.fromisoformat(row['last_scanned_at']) if row['last_scanned_at'] else None
        )