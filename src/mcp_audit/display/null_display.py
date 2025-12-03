"""
NullDisplay - Silent display for --quiet mode and scripting.

This adapter produces no output, useful for automated scripts
or when only the saved session data is needed.
"""

from datetime import datetime

from .base import DisplayAdapter
from .snapshot import DisplaySnapshot


class NullDisplay(DisplayAdapter):
    """Silent display that produces no output."""

    def start(self, snapshot: DisplaySnapshot) -> None:
        """No-op."""
        pass

    def update(self, snapshot: DisplaySnapshot) -> None:
        """No-op."""
        pass

    def on_event(self, tool_name: str, tokens: int, timestamp: datetime) -> None:
        """No-op."""
        pass

    def stop(self, snapshot: DisplaySnapshot) -> None:
        """No-op."""
        pass
