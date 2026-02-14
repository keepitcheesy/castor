"""Data models for Castor."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ItemStatus(Enum):
    """Status of an RSS item."""

    NEW = "new"
    QUEUED = "queued"
    USED = "used"
    SKIPPED = "skipped"


class AnchorStatus(Enum):
    """Status of an anchor."""

    AVAILABLE = "available"
    COOLDOWN = "cooldown"
    USED = "used"


@dataclass
class Feed:
    """RSS feed configuration."""

    id: Optional[int] = None
    url: str = ""
    name: str = ""
    active: bool = True
    last_fetched: Optional[datetime] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Item:
    """RSS feed item."""

    id: Optional[int] = None
    feed_id: int = 0
    guid: str = ""
    title: str = ""
    link: str = ""
    description: str = ""
    content: str = ""
    published: Optional[datetime] = None
    status: ItemStatus = ItemStatus.NEW
    score: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Anchor:
    """Anchor/presenter for programs."""

    id: Optional[int] = None
    name: str = ""
    status: AnchorStatus = AnchorStatus.AVAILABLE
    last_used: Optional[datetime] = None
    cooldown_minutes: int = 60
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Program:
    """Generated program."""

    id: Optional[int] = None
    anchor_id: int = 0
    title: str = ""
    script: str = ""
    item_ids: list[int] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Script:
    """Script template for program generation."""

    id: Optional[int] = None
    name: str = ""
    template: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
