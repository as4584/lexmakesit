"""Version information for the Inventory Manager application."""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# Release metadata
__author__ = "Inventory Manager Team"
__license__ = "MIT"
__copyright__ = "Copyright 2025"

def get_version() -> str:
    """Return the current version string."""
    return __version__

def get_version_info() -> tuple[int, int, int]:
    """Return the current version as a tuple of integers."""
    return __version_info__
