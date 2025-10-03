from .base import Base
from .db import get_session, engine

__all__ = ["Base", "get_session", "engine"]
"""db package: expose subpackages and helpers for importable package layout.

This file makes `shiftbot.db` a proper package so imports like
`from db.models import Attachment` or `import db.models` work when
`PYTHONPATH` or package context is correct. Keep minimal to avoid
top-level side-effects.
"""

__all__ = ["models", "migrations", "base"]
