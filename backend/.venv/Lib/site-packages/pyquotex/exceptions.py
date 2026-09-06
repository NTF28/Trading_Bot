"""Custom exception types raised by pyquotex public APIs."""


class QuotexTimeoutError(TimeoutError):
    """Raised when a Quotex operation exceeds its allotted timeout.

    Wraps asyncio.TimeoutError so callers do not need to import asyncio.
    """
