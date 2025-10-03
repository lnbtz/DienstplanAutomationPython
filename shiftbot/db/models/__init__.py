"""Import all model modules to ensure they register with Base.metadata.

This file is intentionally lightweight: it imports the modules which define
SQLAlchemy models but avoids executing heavy side-effects.
"""
from . import attachment
from . import message
from . import event
from . import run

__all__ = ["attachment", "message", "event", "run"]
