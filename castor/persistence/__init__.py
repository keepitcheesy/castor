"""Database persistence layer for Castor."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from castor.models import (
    Anchor,
    AnchorStatus,
    Feed,
    Item,
    ItemStatus,
    Program,
    Script,
)


class Database:
    """SQLite database manager for Castor."""

    def __init__(self, db_path: str = "castor.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._initialize_schema()

    def _connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _initialize_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Feeds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                last_fetched TEXT,
                last_modified TEXT,
                etag TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                guid TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                description TEXT,
                content TEXT,
                published TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                score REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (feed_id) REFERENCES feeds(id)
            )
        """)

        # Anchors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'available',
                last_used TEXT,
                cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                created_at TEXT NOT NULL
            )
        """)

        # Programs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anchor_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                script TEXT NOT NULL,
                item_ids TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                FOREIGN KEY (anchor_id) REFERENCES anchors(id)
            )
        """)

        # Scripts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                template TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_feed_id ON items(feed_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anchors_status ON anchors(status)")

        self.conn.commit()

    # Feed operations
    def add_feed(self, feed: Feed) -> int:
        """Add a new feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO feeds (url, name, active, last_fetched, last_modified, etag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                feed.url,
                feed.name,
                1 if feed.active else 0,
                feed.last_fetched.isoformat() if feed.last_fetched else None,
                feed.last_modified,
                feed.etag,
                feed.created_at.isoformat(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_feed(self, feed_id: int) -> Optional[Feed]:
        """Get feed by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_feed(row)
        return None

    def get_all_feeds(self, active_only: bool = False) -> List[Feed]:
        """Get all feeds."""
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM feeds WHERE active = 1")
        else:
            cursor.execute("SELECT * FROM feeds")
        return [self._row_to_feed(row) for row in cursor.fetchall()]

    def update_feed(self, feed: Feed):
        """Update feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE feeds
            SET url = ?, name = ?, active = ?, last_fetched = ?, last_modified = ?, etag = ?
            WHERE id = ?
        """,
            (
                feed.url,
                feed.name,
                1 if feed.active else 0,
                feed.last_fetched.isoformat() if feed.last_fetched else None,
                feed.last_modified,
                feed.etag,
                feed.id,
            ),
        )
        self.conn.commit()

    def _row_to_feed(self, row) -> Feed:
        """Convert database row to Feed object."""
        return Feed(
            id=row["id"],
            url=row["url"],
            name=row["name"],
            active=bool(row["active"]),
            last_fetched=(
                datetime.fromisoformat(row["last_fetched"]) if row["last_fetched"] else None
            ),
            last_modified=row["last_modified"],
            etag=row["etag"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # Item operations
    def add_item(self, item: Item) -> Optional[int]:
        """Add a new item. Returns None if duplicate guid."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO items (feed_id, guid, title, link, description, content,
                                 published, status, score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    item.feed_id,
                    item.guid,
                    item.title,
                    item.link,
                    item.description,
                    item.content,
                    item.published.isoformat() if item.published else None,
                    item.status.value,
                    item.score,
                    item.created_at.isoformat(),
                ),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Duplicate guid
            return None

    def get_item(self, item_id: int) -> Optional[Item]:
        """Get item by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_item(row)
        return None

    def get_items_by_status(self, status: ItemStatus, limit: Optional[int] = None) -> List[Item]:
        """Get items by status."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM items WHERE status = ? ORDER BY score DESC, published DESC"
        params = [status.value]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor.execute(query, params)
        return [self._row_to_item(row) for row in cursor.fetchall()]

    def update_item(self, item: Item):
        """Update item."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE items
            SET feed_id = ?, guid = ?, title = ?, link = ?, description = ?, content = ?,
                published = ?, status = ?, score = ?
            WHERE id = ?
        """,
            (
                item.feed_id,
                item.guid,
                item.title,
                item.link,
                item.description,
                item.content,
                item.published.isoformat() if item.published else None,
                item.status.value,
                item.score,
                item.id,
            ),
        )
        self.conn.commit()

    def _row_to_item(self, row) -> Item:
        """Convert database row to Item object."""
        return Item(
            id=row["id"],
            feed_id=row["feed_id"],
            guid=row["guid"],
            title=row["title"],
            link=row["link"],
            description=row["description"],
            content=row["content"],
            published=datetime.fromisoformat(row["published"]) if row["published"] else None,
            status=ItemStatus(row["status"]),
            score=row["score"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # Anchor operations
    def add_anchor(self, anchor: Anchor) -> int:
        """Add a new anchor."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO anchors (name, status, last_used, cooldown_minutes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                anchor.name,
                anchor.status.value,
                anchor.last_used.isoformat() if anchor.last_used else None,
                anchor.cooldown_minutes,
                anchor.created_at.isoformat(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_anchor(self, anchor_id: int) -> Optional[Anchor]:
        """Get anchor by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM anchors WHERE id = ?", (anchor_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_anchor(row)
        return None

    def get_all_anchors(self) -> List[Anchor]:
        """Get all anchors."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM anchors")
        return [self._row_to_anchor(row) for row in cursor.fetchall()]

    def get_available_anchors(self) -> List[Anchor]:
        """Get anchors that are available (not on cooldown)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM anchors WHERE status = ?", (AnchorStatus.AVAILABLE.value,))
        return [self._row_to_anchor(row) for row in cursor.fetchall()]

    def update_anchor(self, anchor: Anchor):
        """Update anchor."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE anchors
            SET name = ?, status = ?, last_used = ?, cooldown_minutes = ?
            WHERE id = ?
        """,
            (
                anchor.name,
                anchor.status.value,
                anchor.last_used.isoformat() if anchor.last_used else None,
                anchor.cooldown_minutes,
                anchor.id,
            ),
        )
        self.conn.commit()

    def _row_to_anchor(self, row) -> Anchor:
        """Convert database row to Anchor object."""
        return Anchor(
            id=row["id"],
            name=row["name"],
            status=AnchorStatus(row["status"]),
            last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            cooldown_minutes=row["cooldown_minutes"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # Program operations
    def add_program(self, program: Program) -> int:
        """Add a new program."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO programs (anchor_id, title, script, item_ids, generated_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                program.anchor_id,
                program.title,
                program.script,
                json.dumps(program.item_ids),
                program.generated_at.isoformat(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_program(self, program_id: int) -> Optional[Program]:
        """Get program by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM programs WHERE id = ?", (program_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_program(row)
        return None

    def get_all_programs(self, limit: Optional[int] = None) -> List[Program]:
        """Get all programs."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM programs ORDER BY generated_at DESC"
        if limit:
            query += " LIMIT ?"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        return [self._row_to_program(row) for row in cursor.fetchall()]

    def _row_to_program(self, row) -> Program:
        """Convert database row to Program object."""
        return Program(
            id=row["id"],
            anchor_id=row["anchor_id"],
            title=row["title"],
            script=row["script"],
            item_ids=json.loads(row["item_ids"]),
            generated_at=datetime.fromisoformat(row["generated_at"]),
        )

    # Script operations
    def add_script(self, script: Script) -> int:
        """Add a new script template."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO scripts (name, template, active, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                script.name,
                script.template,
                1 if script.active else 0,
                script.created_at.isoformat(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_active_script(self) -> Optional[Script]:
        """Get the active script template."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scripts WHERE active = 1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return self._row_to_script(row)
        return None

    def _row_to_script(self, row) -> Script:
        """Convert database row to Script object."""
        return Script(
            id=row["id"],
            name=row["name"],
            template=row["template"],
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
