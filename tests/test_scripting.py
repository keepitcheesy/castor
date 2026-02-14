"""Tests for script generation."""

import os
import tempfile

import pytest

from castor.models import Anchor, Feed, Item, ItemStatus, Script
from castor.persistence import Database
from castor.scripting import ScriptGenerator


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    database = Database(path)
    yield database

    database.close()
    os.unlink(path)


def test_generate_program(db):
    """Test program generation."""
    generator = ScriptGenerator(db)

    # Add anchor
    anchor = Anchor(name="Test Anchor")
    anchor.id = db.add_anchor(anchor)

    # Add feed
    feed = Feed(url="http://ex.com/rss", name="Test")
    feed_id = db.add_feed(feed)

    # Add items
    items = []
    for i in range(3):
        item = Item(
            feed_id=feed_id,
            guid=f"guid-{i}",
            title=f"Article {i}",
            link=f"http://ex.com/{i}",
            description=f"Description {i}",
            status=ItemStatus.QUEUED,
        )
        item.id = db.add_item(item)
        items.append(item)

    # Generate program
    program = generator.generate_program(anchor, items)

    # Verify program
    assert program.id is not None
    assert program.anchor_id == anchor.id
    assert len(program.item_ids) == 3
    assert "Test Anchor" in program.script
    assert "Article 0" in program.script

    # Verify items marked as used
    for item in items:
        updated_item = db.get_item(item.id)
        assert updated_item.status == ItemStatus.USED


def test_script_template_variables(db):
    """Test script template variable replacement."""
    generator = ScriptGenerator(db)

    # Add custom template
    script = Script(
        name="Custom",
        template="Hello {anchor_name} on {date}. We have {item_count} items.\n{items}",
        active=True,
    )
    db.add_script(script)

    # Add anchor
    anchor = Anchor(name="Alice")
    anchor.id = db.add_anchor(anchor)

    # Add feed and items
    feed = Feed(url="http://ex.com/rss", name="Test")
    feed_id = db.add_feed(feed)

    items = []
    item = Item(
        feed_id=feed_id,
        guid="guid-1",
        title="Test Article",
        link="http://ex.com/1",
        status=ItemStatus.QUEUED,
    )
    item.id = db.add_item(item)
    items.append(item)

    # Generate program
    program = generator.generate_program(anchor, items)

    # Check variables were replaced
    assert "Alice" in program.script
    assert "1 items" in program.script or "1" in program.script
    assert "Test Article" in program.script
