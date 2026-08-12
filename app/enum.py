"""Custom enum."""

from enum import StrEnum


class HyphenStrEnum(StrEnum):
    """Enum where members are also (and must be) strings.

    When using auto(), the resulting value is the hyphenated lower-cased version of the member name.
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:  # ruff: ignore[unused-static-method-argument]
        """Return the hyphenated lower-cased version of the member name."""
        return name.lower().replace("_", "-")


class UpperStrEnum(StrEnum):
    """Enum where members are also (and must be) strings.

    When using auto(), the resulting value is the upper-cased version of the member name.
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:  # ruff: ignore[unused-static-method-argument]
        """Return the upper-cased version of the member name."""
        return name.upper()
