from __future__ import annotations
from shiftbot.db.base import Base
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text

class Run(Base):
    """
    Optional audit row per pipeline run (for summaries/alerts).
    """
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at_utc:  Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    scanned:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parsed:   Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Optional freeform notes for status messages per run
    notes: Mapped[Optional[str]] = mapped_column(Text)
