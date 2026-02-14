"""Tests for data models."""


from castor.models import Anchor, AnchorStatus, Feed, Item, ItemStatus, Program, Script


def test_feed_creation():
    """Test Feed model creation."""
    feed = Feed(
        url="https://example.com/rss",
        name="Example Feed",
        active=True,
    )
    assert feed.url == "https://example.com/rss"
    assert feed.name == "Example Feed"
    assert feed.active is True
    assert feed.id is None


def test_item_creation():
    """Test Item model creation."""
    item = Item(
        feed_id=1,
        guid="unique-id",
        title="Test Item",
        link="https://example.com/item",
        description="Test description",
        status=ItemStatus.NEW,
    )
    assert item.title == "Test Item"
    assert item.status == ItemStatus.NEW
    assert item.score == 0.0


def test_anchor_creation():
    """Test Anchor model creation."""
    anchor = Anchor(
        name="Test Anchor",
        status=AnchorStatus.AVAILABLE,
        cooldown_minutes=60,
    )
    assert anchor.name == "Test Anchor"
    assert anchor.status == AnchorStatus.AVAILABLE
    assert anchor.cooldown_minutes == 60


def test_program_creation():
    """Test Program model creation."""
    program = Program(
        anchor_id=1,
        title="Test Program",
        script="Hello world",
        item_ids=[1, 2, 3],
    )
    assert program.title == "Test Program"
    assert len(program.item_ids) == 3


def test_script_creation():
    """Test Script model creation."""
    script = Script(
        name="Test Template",
        template="Hello {anchor_name}",
        active=True,
    )
    assert script.name == "Test Template"
    assert script.active is True
