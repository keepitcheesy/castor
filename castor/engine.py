"""Core engine for Castor application."""

import threading
import time
from typing import Optional

from castor.ingestion import RSSIngestion
from castor.models import ItemStatus
from castor.persistence import Database
from castor.scoring import AnchorScheduler, ContentScheduler, DeduplicationSystem, ScoringSystem
from castor.scripting import ScriptGenerator


class CastorEngine:
    """Main engine coordinating all Castor systems."""

    def __init__(self, db_path: str = "castor.db"):
        """Initialize Castor engine."""
        self.db = Database(db_path)
        self.ingestion = RSSIngestion(self.db)
        self.scoring = ScoringSystem(self.db)
        self.dedup = DeduplicationSystem(self.db)
        self.anchor_scheduler = AnchorScheduler(self.db)
        self.content_scheduler = ContentScheduler(
            self.db, self.scoring, self.dedup, self.anchor_scheduler
        )
        self.script_generator = ScriptGenerator(self.db)

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.status_message = "Stopped"
        self.last_fetch_time: Optional[float] = None
        self.last_program_time: Optional[float] = None

        # Configuration
        self.fetch_interval_seconds = 300  # 5 minutes
        self.program_interval_seconds = 600  # 10 minutes
        self.items_per_program = 5

    def start(self):
        """Start the Castor engine."""
        if self.running:
            return

        self.running = True
        self.status_message = "Starting..."
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the Castor engine."""
        if not self.running:
            return

        self.running = False
        self.status_message = "Stopping..."
        if self.thread:
            self.thread.join(timeout=5)
        self.status_message = "Stopped"

    def _run_loop(self):
        """Main processing loop."""
        self.status_message = "Running"

        while self.running:
            try:
                current_time = time.time()

                # Check if it's time to fetch feeds
                if (
                    self.last_fetch_time is None
                    or (current_time - self.last_fetch_time) >= self.fetch_interval_seconds
                ):
                    self._fetch_feeds()
                    self.last_fetch_time = current_time

                # Check if it's time to generate a program
                if (
                    self.last_program_time is None
                    or (current_time - self.last_program_time) >= self.program_interval_seconds
                ):
                    self._generate_program()
                    self.last_program_time = current_time

                # Update anchor cooldowns
                self.anchor_scheduler.update_anchor_cooldowns()

                # Sleep before next iteration
                time.sleep(10)

            except Exception as e:
                self.status_message = f"Error: {e}"
                print(f"Engine error: {e}")

    def _fetch_feeds(self):
        """Fetch all RSS feeds."""
        try:
            self.status_message = "Fetching feeds..."
            new_items_count = self.ingestion.fetch_all_feeds()

            if new_items_count > 0:
                # Score new items
                self.scoring.score_all_new_items()
                self.status_message = f"Found {new_items_count} new items"
            else:
                self.status_message = "No new items"

        except Exception as e:
            self.status_message = f"Feed fetch error: {e}"
            print(f"Feed fetch error: {e}")

    def _generate_program(self):
        """Generate a program if conditions are met."""
        try:
            # Check if we have an available anchor
            anchor = self.anchor_scheduler.select_available_anchor()
            if not anchor:
                self.status_message = "No available anchors"
                return

            # Prepare content queue
            items = self.content_scheduler.prepare_content_queue(max_items=self.items_per_program)

            if not items:
                self.status_message = "No items available for program"
                return

            # Queue items
            self.content_scheduler.queue_items_for_program(items)

            # Generate program
            self.status_message = "Generating program..."
            program = self.script_generator.generate_program(anchor, items)

            # Mark anchor as used
            self.anchor_scheduler.mark_anchor_used(anchor)

            self.status_message = f"Generated program: {program.title}"

        except Exception as e:
            self.status_message = f"Program generation error: {e}"
            print(f"Program generation error: {e}")

    def get_status(self) -> dict:
        """Get current engine status."""
        feeds = self.db.get_all_feeds()
        new_items = self.db.get_items_by_status(ItemStatus.NEW)
        queued_items = self.db.get_items_by_status(ItemStatus.QUEUED)
        programs = self.db.get_all_programs(limit=10)
        anchors = self.db.get_all_anchors()

        return {
            "running": self.running,
            "status_message": self.status_message,
            "feeds_count": len(feeds),
            "new_items_count": len(new_items),
            "queued_items_count": len(queued_items),
            "programs_count": len(programs),
            "anchors_count": len(anchors),
            "available_anchors": len([a for a in anchors if a.status.value == "available"]),
        }

    def close(self):
        """Close the engine and database."""
        self.stop()
        self.db.close()
