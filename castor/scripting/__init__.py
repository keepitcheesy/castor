"""Script generation system for programs."""

from datetime import datetime
from typing import List

from castor.models import Anchor, Item, ItemStatus, Program, Script
from castor.persistence import Database


class ScriptGenerator:
    """Generate program scripts from items and templates."""

    def __init__(self, db: Database):
        """Initialize script generator."""
        self.db = db

    def generate_program(self, anchor: Anchor, items: List[Item]) -> Program:
        """
        Generate a program script from items using the active template.

        Args:
            anchor: Anchor/presenter for the program
            items: List of items to include in the program

        Returns:
            Generated Program object
        """
        # Get active script template
        script_template = self.db.get_active_script()
        if not script_template:
            script_template = self._get_default_template()

        # Generate script content
        script_content = self._generate_script_content(anchor, items, script_template.template)

        # Generate program title
        title = self._generate_title(items)

        # Create program
        program = Program(
            anchor_id=anchor.id,
            title=title,
            script=script_content,
            item_ids=[item.id for item in items],
            generated_at=datetime.utcnow(),
        )

        # Save program
        program.id = self.db.add_program(program)

        # Mark items as used
        for item in items:
            item.status = ItemStatus.USED
            self.db.update_item(item)

        return program

    def _generate_script_content(self, anchor: Anchor, items: List[Item], template: str) -> str:
        """
        Generate script content from template.

        Template variables:
        - {anchor_name}: Name of the anchor
        - {date}: Current date
        - {item_count}: Number of items
        - {items}: Formatted list of items

        Args:
            anchor: Anchor for the program
            items: List of items
            template: Script template string

        Returns:
            Generated script content
        """
        # Format items section
        items_section = self._format_items(items)

        # Replace template variables
        script = template.replace("{anchor_name}", anchor.name)
        script = script.replace("{date}", datetime.utcnow().strftime("%B %d, %Y"))
        script = script.replace("{item_count}", str(len(items)))
        script = script.replace("{items}", items_section)

        return script

    def _format_items(self, items: List[Item]) -> str:
        """Format items for script inclusion."""
        formatted = []

        for i, item in enumerate(items, 1):
            item_text = f"\n{i}. {item.title}\n"
            if item.description:
                # Limit description length
                desc = item.description[:300]
                if len(item.description) > 300:
                    desc += "..."
                item_text += f"   {desc}\n"
            if item.link:
                item_text += f"   More at: {item.link}\n"
            formatted.append(item_text)

        return "\n".join(formatted)

    def _generate_title(self, items: List[Item]) -> str:
        """Generate a title for the program."""
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        if items:
            return f"News Digest - {date_str} ({len(items)} items)"
        return f"News Digest - {date_str}"

    def _get_default_template(self) -> Script:
        """Get default script template if none is active."""
        return Script(
            name="Default Template",
            template="""Hello, I'm {anchor_name}, and welcome to today's news digest for {date}.

We have {item_count} stories for you today.

{items}

That's all for today's digest. Thank you for listening!
""",
            active=True,
        )
