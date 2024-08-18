"""Common utilities."""

import time


def get_current_timestamp() -> str:
    """Return the current timestamp in seconds formatted as string."""
    return str(int(time.time()))
