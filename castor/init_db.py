"""Database initialization and sample data."""

from castor.models import Anchor, Feed, Script
from castor.persistence import Database


def initialize_database(db_path: str = "castor.db"):
    """Initialize database with sample data."""
    db = Database(db_path)

    # Add sample feeds
    feeds = [
        Feed(
            url="https://news.ycombinator.com/rss",
            name="Hacker News",
            active=True,
        ),
        Feed(
            url="https://www.reddit.com/r/technology/.rss",
            name="Reddit Technology",
            active=True,
        ),
    ]

    for feed in feeds:
        try:
            db.add_feed(feed)
            print(f"Added feed: {feed.name}")
        except Exception as e:
            print(f"Feed {feed.name} may already exist: {e}")

    # Add sample anchors
    anchors = [
        Anchor(name="Alice", cooldown_minutes=60),
        Anchor(name="Bob", cooldown_minutes=90),
        Anchor(name="Charlie", cooldown_minutes=120),
    ]

    for anchor in anchors:
        try:
            db.add_anchor(anchor)
            print(f"Added anchor: {anchor.name}")
        except Exception as e:
            print(f"Anchor {anchor.name} may already exist: {e}")

    # Add default script template
    script = Script(
        name="News Digest Template",
        template="""Hello, I'm {anchor_name}, and welcome to today's news digest for {date}.

We have {item_count} stories for you today.

{items}

That's all for today's digest. Thank you for listening!
""",
        active=True,
    )

    try:
        db.add_script(script)
        print("Added default script template")
    except Exception as e:
        print(f"Script template may already exist: {e}")

    db.close()
    print("\nDatabase initialized successfully!")


if __name__ == "__main__":
    initialize_database()
