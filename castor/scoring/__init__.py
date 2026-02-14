"""Scoring, deduplication, and scheduling system."""

from datetime import datetime, timedelta
from typing import List, Optional

from castor.models import Anchor, AnchorStatus, Item, ItemStatus
from castor.persistence import Database


class ScoringSystem:
    """Score items based on various factors."""

    def __init__(self, db: Database):
        """Initialize scoring system."""
        self.db = db

    def score_item(self, item: Item) -> float:
        """
        Calculate score for an item based on various factors.

        Scoring factors:
        - Recency: More recent items score higher
        - Title length: Prefer items with substantial titles
        - Content length: Prefer items with more content
        - Source quality: Can be extended with feed-based scoring

        Returns:
            Score between 0.0 and 100.0
        """
        score = 0.0

        # Recency score (0-40 points)
        if item.published:
            age_hours = (datetime.utcnow() - item.published).total_seconds() / 3600
            # Exponential decay: full points for < 1 hour, half at 24 hours
            recency_score = 40.0 * (0.5 ** (age_hours / 24))
            score += min(recency_score, 40.0)
        else:
            score += 20.0  # Default for items without publish date

        # Title score (0-30 points)
        title_len = len(item.title)
        if 20 <= title_len <= 100:
            score += 30.0
        elif title_len > 100:
            score += 20.0
        elif title_len > 10:
            score += 15.0

        # Content score (0-30 points)
        content_len = len(item.content or item.description or "")
        if content_len > 1000:
            score += 30.0
        elif content_len > 500:
            score += 25.0
        elif content_len > 200:
            score += 20.0
        elif content_len > 100:
            score += 10.0

        return min(score, 100.0)

    def score_all_new_items(self):
        """Score all items with NEW status."""
        items = self.db.get_items_by_status(ItemStatus.NEW)
        for item in items:
            item.score = self.score_item(item)
            self.db.update_item(item)


class DeduplicationSystem:
    """Detect and handle duplicate items."""

    def __init__(self, db: Database):
        """Initialize deduplication system."""
        self.db = db

    def deduplicate_by_title(
        self, items: List[Item], similarity_threshold: float = 0.8
    ) -> List[Item]:
        """
        Remove items with very similar titles.

        Simple implementation using normalized title matching.
        In production, this could use more sophisticated similarity measures.

        Args:
            items: List of items to deduplicate
            similarity_threshold: How similar titles need to be (0.0-1.0)

        Returns:
            Deduplicated list of items
        """
        if not items:
            return []

        unique_items = []
        seen_titles = set()

        for item in items:
            # Normalize title for comparison
            normalized = self._normalize_title(item.title)

            # Check for duplicates
            is_duplicate = False
            for seen in seen_titles:
                if self._title_similarity(normalized, seen) >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)
                seen_titles.add(normalized)

        return unique_items

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        return title.lower().strip()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate simple similarity between two titles.

        Uses a basic character-overlap approach.
        """
        if title1 == title2:
            return 1.0

        # Count matching characters
        set1 = set(title1)
        set2 = set(title2)
        intersection = set1 & set2
        union = set1 | set2

        if not union:
            return 0.0

        return len(intersection) / len(union)


class AnchorScheduler:
    """Manage anchor selection and cooldown."""

    def __init__(self, db: Database):
        """Initialize anchor scheduler."""
        self.db = db

    def select_available_anchor(self) -> Optional[Anchor]:
        """
        Select an available anchor for program generation.

        Considers:
        - Anchor status (must be AVAILABLE)
        - Cooldown period (if last_used exists)

        Returns:
            Available anchor or None if all are on cooldown
        """
        anchors = self.db.get_all_anchors()

        available = []
        now = datetime.utcnow()

        for anchor in anchors:
            # Check if anchor is available
            if anchor.status != AnchorStatus.AVAILABLE:
                continue

            # Check cooldown
            if anchor.last_used:
                time_since_use = (now - anchor.last_used).total_seconds() / 60
                if time_since_use < anchor.cooldown_minutes:
                    continue

            available.append(anchor)

        if not available:
            return None

        # Return anchor that was used longest ago (or never used)
        available.sort(key=lambda a: a.last_used or datetime.min)
        return available[0]

    def mark_anchor_used(self, anchor: Anchor):
        """Mark anchor as used and update cooldown status."""
        anchor.status = AnchorStatus.COOLDOWN
        anchor.last_used = datetime.utcnow()
        self.db.update_anchor(anchor)

    def update_anchor_cooldowns(self):
        """Update anchor statuses based on cooldown timers."""
        anchors = self.db.get_all_anchors()
        now = datetime.utcnow()

        for anchor in anchors:
            if anchor.status == AnchorStatus.COOLDOWN and anchor.last_used:
                time_since_use = (now - anchor.last_used).total_seconds() / 60
                if time_since_use >= anchor.cooldown_minutes:
                    anchor.status = AnchorStatus.AVAILABLE
                    self.db.update_anchor(anchor)


class ContentScheduler:
    """Manage content queue and scheduling."""

    def __init__(
        self,
        db: Database,
        scoring: ScoringSystem,
        dedup: DeduplicationSystem,
        anchor_scheduler: AnchorScheduler,
    ):
        """Initialize content scheduler."""
        self.db = db
        self.scoring = scoring
        self.dedup = dedup
        self.anchor_scheduler = anchor_scheduler

    def prepare_content_queue(self, max_items: int = 10) -> List[Item]:
        """
        Prepare content queue with scored and deduplicated items.

        Args:
            max_items: Maximum number of items to return

        Returns:
            List of items ready for program generation
        """
        # Get all NEW items
        items = self.db.get_items_by_status(ItemStatus.NEW)

        if not items:
            return []

        # Score items if not already scored
        for item in items:
            if item.score == 0.0:
                item.score = self.scoring.score_item(item)
                self.db.update_item(item)

        # Sort by score
        items.sort(key=lambda x: x.score, reverse=True)

        # Deduplicate
        items = self.dedup.deduplicate_by_title(items)

        # Return top N items
        return items[:max_items]

    def queue_items_for_program(self, items: List[Item]):
        """Mark items as queued."""
        for item in items:
            item.status = ItemStatus.QUEUED
            self.db.update_item(item)
