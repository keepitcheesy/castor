"""Tests for scoring and scheduling systems."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from castor.models import Anchor, AnchorStatus, Item, ItemStatus
from castor.persistence import Database
from castor.scoring import AnchorScheduler, ContentScheduler, DeduplicationSystem, ScoringSystem


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    database = Database(path)
    yield database

    database.close()
    os.unlink(path)


def test_scoring_system(db):
    """Test item scoring."""
    scoring = ScoringSystem(db)

    # Create items with different characteristics
    recent_item = Item(
        feed_id=1,
        guid="recent",
        title="Recent Article with Good Title",
        link="http://ex.com/1",
        content="This is a substantial piece of content that should score well " * 20,
        published=datetime.utcnow(),
    )

    old_item = Item(
        feed_id=1,
        guid="old",
        title="Old Article",
        link="http://ex.com/2",
        content="Short",
        published=datetime.utcnow() - timedelta(days=7),
    )

    # Score items
    recent_score = scoring.score_item(recent_item)
    old_score = scoring.score_item(old_item)

    # Recent item with good content should score higher
    assert recent_score > old_score
    assert recent_score > 0
    assert old_score > 0


def test_deduplication_system(db):
    """Test deduplication."""
    dedup = DeduplicationSystem(db)

    items = [
        Item(feed_id=1, guid="1", title="Breaking News Today", link="http://ex.com/1"),
        Item(feed_id=1, guid="2", title="Breaking News Today", link="http://ex.com/2"),
        Item(feed_id=1, guid="3", title="Completely Different Story", link="http://ex.com/3"),
    ]

    unique_items = dedup.deduplicate_by_title(items)

    # Should remove one duplicate
    assert len(unique_items) == 2


def test_anchor_scheduler_select_available(db):
    """Test anchor selection."""
    scheduler = AnchorScheduler(db)

    # Add anchors
    anchor1 = Anchor(name="Anchor 1", status=AnchorStatus.AVAILABLE)
    anchor2 = Anchor(
        name="Anchor 2",
        status=AnchorStatus.COOLDOWN,
        last_used=datetime.utcnow(),
        cooldown_minutes=60,
    )

    db.add_anchor(anchor1)
    db.add_anchor(anchor2)

    # Should select available anchor
    selected = scheduler.select_available_anchor()
    assert selected is not None
    assert selected.name == "Anchor 1"


def test_anchor_scheduler_cooldown(db):
    """Test anchor cooldown logic."""
    scheduler = AnchorScheduler(db)

    # Add anchor that was used 2 hours ago (cooldown should be over)
    anchor = Anchor(
        name="Test Anchor",
        status=AnchorStatus.COOLDOWN,
        last_used=datetime.utcnow() - timedelta(hours=2),
        cooldown_minutes=60,
    )
    anchor_id = db.add_anchor(anchor)

    # Update cooldowns
    scheduler.update_anchor_cooldowns()

    # Anchor should now be available
    updated_anchor = db.get_anchor(anchor_id)
    assert updated_anchor.status == AnchorStatus.AVAILABLE


def test_content_scheduler_prepare_queue(db):
    """Test content queue preparation."""
    scoring = ScoringSystem(db)
    dedup = DeduplicationSystem(db)
    anchor_scheduler = AnchorScheduler(db)
    scheduler = ContentScheduler(db, scoring, dedup, anchor_scheduler)

    # Add feed
    from castor.models import Feed

    feed = Feed(url="http://ex.com/rss", name="Test")
    feed_id = db.add_feed(feed)

    # Add items with distinct titles to avoid deduplication
    titles = [
        "Breaking News About Technology",
        "Sports Update From Today",
        "Weather Forecast for Tomorrow",
        "Business Market Analysis",
        "Entertainment Celebrity News",
    ]
    for i in range(5):
        item = Item(
            feed_id=feed_id,
            guid=f"guid-{i}",
            title=titles[i],
            link=f"http://ex.com/{i}",
            status=ItemStatus.NEW,
            score=float(i),
        )
        db.add_item(item)

    # Prepare queue
    queue = scheduler.prepare_content_queue(max_items=3)

    # Should return top 3 items by score
    assert len(queue) == 3
    assert queue[0].score >= queue[1].score
