"""RSS feed ingestion system."""

from datetime import datetime
from typing import List, Optional

import feedparser
import requests

from castor.models import Feed, Item, ItemStatus
from castor.persistence import Database


class RSSIngestion:
    """RSS feed ingestion and parsing."""

    def __init__(self, db: Database):
        """Initialize RSS ingestion system."""
        self.db = db

    def fetch_feed(self, feed: Feed) -> List[Item]:
        """
        Fetch and parse RSS feed, returning new items.

        Args:
            feed: Feed to fetch

        Returns:
            List of newly discovered items
        """
        headers = {}
        if feed.etag:
            headers["If-None-Match"] = feed.etag
        if feed.last_modified:
            headers["If-Modified-Since"] = feed.last_modified

        try:
            response = requests.get(feed.url, headers=headers, timeout=30)
            response.raise_for_status()

            # Check if feed was modified
            if response.status_code == 304:
                # Not modified
                feed.last_fetched = datetime.utcnow()
                self.db.update_feed(feed)
                return []

            # Parse feed
            parsed = feedparser.parse(response.content)

            # Update feed metadata
            feed.last_fetched = datetime.utcnow()
            feed.etag = response.headers.get("ETag")
            feed.last_modified = response.headers.get("Last-Modified")
            self.db.update_feed(feed)

            # Process entries
            new_items = []
            for entry in parsed.entries:
                item = self._parse_entry(entry, feed.id)
                if item:
                    item_id = self.db.add_item(item)
                    if item_id:  # Successfully added (not duplicate)
                        item.id = item_id
                        new_items.append(item)

            return new_items

        except Exception as e:
            print(f"Error fetching feed {feed.url}: {e}")
            return []

    def _parse_entry(self, entry, feed_id: int) -> Optional[Item]:
        """Parse a feed entry into an Item."""
        # Extract GUID
        guid = entry.get("id") or entry.get("link", "")
        if not guid:
            return None

        # Extract title
        title = entry.get("title", "Untitled")

        # Extract link
        link = entry.get("link", "")

        # Extract description
        description = entry.get("summary", "")

        # Extract content
        content = ""
        if "content" in entry:
            content = entry.content[0].get("value", "") if entry.content else ""
        elif description:
            content = description

        # Extract published date
        published = None
        if "published_parsed" in entry and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        return Item(
            feed_id=feed_id,
            guid=guid,
            title=title,
            link=link,
            description=description,
            content=content,
            published=published,
            status=ItemStatus.NEW,
        )

    def fetch_all_feeds(self) -> int:
        """
        Fetch all active feeds.

        Returns:
            Total number of new items discovered
        """
        feeds = self.db.get_all_feeds(active_only=True)
        total_new_items = 0

        for feed in feeds:
            new_items = self.fetch_feed(feed)
            total_new_items += len(new_items)

        return total_new_items
