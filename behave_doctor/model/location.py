"""Shared utility for extracting a Path from a behave-model location object."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["location_line", "location_path"]


def location_path(location: Any) -> Path | None:
    """Return a :class:`~pathlib.Path` for a behave-model location, or ``None``.

    Args:
        location: A behave-model location object with a ``filename`` attribute.
    """
    filename = getattr(location, "filename", "") or ""
    return Path(filename) if filename else None


def location_line(location: Any) -> int | None:
    """Return the 1-indexed line number from a behave-model location, or ``None``.

    Args:
        location: A behave-model location object with a ``line`` attribute.
    """
    line = getattr(location, "line", None)
    return line if line else None
