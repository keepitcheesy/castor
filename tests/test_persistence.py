"""Tests for persistence layer."""

import os
import tempfile

import pytest

from castor.models import Anchor, AnchorStatus, Feed, Item, ItemStatus, Program, Script
from castor.persistence import Database


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    database = Database(path)
    yield database

    database.close()
    os.unlink(path)


def test_database_initialization(db):
    """Test database schema initialization."""
    assert db.conn is not None


def test_add_and_get_feed(db):
    """Test adding and retrieving a feed."""
    feed = Feed(url="https://example.com/rss", name="Test Feed", active=True)
    feed_id = db.add_feed(feed)

    assert feed_id is not None

    retrieved_feed = db.get_feed(feed_id)
    assert retrieved_feed.url == feed.url
    assert retrieved_feed.name == feed.name
    assert retrieved_feed.active == feed.active


def test_get_all_feeds(db):
    """Test retrieving all feeds."""
    feed1 = Feed(url="https://example1.com/rss", name="Feed 1", active=True)
    feed2 = Feed(url="https://example2.com/rss", name="Feed 2", active=False)

    db.add_feed(feed1)
    db.add_feed(feed2)

    all_feeds = db.get_all_feeds()
    assert len(all_feeds) == 2

    active_feeds = db.get_all_feeds(active_only=True)
    assert len(active_feeds) == 1


def test_add_and_get_item(db):
    """Test adding and retrieving an item."""
    # First add a feed
    feed = Feed(url="https://example.com/rss", name="Test Feed")
    feed_id = db.add_feed(feed)

    # Add an item
    item = Item(
        feed_id=feed_id,
        guid="unique-123",
        title="Test Item",
        link="https://example.com/item",
        status=ItemStatus.NEW,
    )
    item_id = db.add_item(item)

    assert item_id is not None

    retrieved_item = db.get_item(item_id)
    assert retrieved_item.title == item.title
    assert retrieved_item.guid == item.guid


def test_duplicate_item_guid(db):
    """Test that duplicate GUIDs are handled."""
    feed = Feed(url="https://example.com/rss", name="Test Feed")
    feed_id = db.add_feed(feed)

    item1 = Item(feed_id=feed_id, guid="same-guid", title="Item 1", link="http://ex.com/1")
    item2 = Item(feed_id=feed_id, guid="same-guid", title="Item 2", link="http://ex.com/2")

    id1 = db.add_item(item1)
    id2 = db.add_item(item2)

    assert id1 is not None
    assert id2 is None  # Duplicate should return None


def test_get_items_by_status(db):
    """Test retrieving items by status."""
    feed = Feed(url="https://example.com/rss", name="Test Feed")
    feed_id = db.add_feed(feed)

    item1 = Item(
        feed_id=feed_id,
        guid="guid-1",
        title="Item 1",
        link="http://ex.com/1",
        status=ItemStatus.NEW,
        score=10.0,
    )
    item2 = Item(
        feed_id=feed_id,
        guid="guid-2",
        title="Item 2",
        link="http://ex.com/2",
        status=ItemStatus.NEW,
        score=20.0,
    )
    item3 = Item(
        feed_id=feed_id,
        guid="guid-3",
        title="Item 3",
        link="http://ex.com/3",
        status=ItemStatus.QUEUED,
    )

    db.add_item(item1)
    db.add_item(item2)
    db.add_item(item3)

    new_items = db.get_items_by_status(ItemStatus.NEW)
    assert len(new_items) == 2
    # Should be sorted by score descending
    assert new_items[0].score == 20.0

    queued_items = db.get_items_by_status(ItemStatus.QUEUED)
    assert len(queued_items) == 1


def test_add_and_get_anchor(db):
    """Test adding and retrieving an anchor."""
    anchor = Anchor(name="Test Anchor", cooldown_minutes=60)
    anchor_id = db.add_anchor(anchor)

    retrieved_anchor = db.get_anchor(anchor_id)
    assert retrieved_anchor.name == anchor.name
    assert retrieved_anchor.cooldown_minutes == anchor.cooldown_minutes


def test_get_available_anchors(db):
    """Test retrieving available anchors."""
    anchor1 = Anchor(name="Anchor 1", status=AnchorStatus.AVAILABLE)
    anchor2 = Anchor(name="Anchor 2", status=AnchorStatus.COOLDOWN)

    db.add_anchor(anchor1)
    db.add_anchor(anchor2)

    available = db.get_available_anchors()
    assert len(available) == 1
    assert available[0].name == "Anchor 1"


def test_add_and_get_program(db):
    """Test adding and retrieving a program."""
    # Add anchor first
    anchor = Anchor(name="Test Anchor")
    anchor_id = db.add_anchor(anchor)

    # Add program
    program = Program(
        anchor_id=anchor_id,
        title="Test Program",
        script="Hello world",
        item_ids=[1, 2, 3],
    )
    program_id = db.add_program(program)

    retrieved_program = db.get_program(program_id)
    assert retrieved_program.title == program.title
    assert len(retrieved_program.item_ids) == 3


def test_add_and_get_script(db):
    """Test adding and retrieving a script."""
    script = Script(name="Test Template", template="Hello {anchor_name}", active=True)
    db.add_script(script)

    active_script = db.get_active_script()
    assert active_script is not None
    assert active_script.name == script.name
