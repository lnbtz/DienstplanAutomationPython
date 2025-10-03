from __future__ import annotations
from shiftbot.db.base import Base
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    CheckConstraint, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attachment import Attachment
    from .message import Message

from sqlalchemy import Enum as SAEnum

# event status enum
EventStatus = SAEnum(
    "planned", "synced", "cancelled", name="event_status",
)

class Event(Base):
    __tablename__ = "events"

    event_uid: Mapped[str] = mapped_column(String(128), primary_key=True)

    attachment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attachments.id", ondelete="RESTRICT"), index=True
    )
    source_msg_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("messages.msg_id", ondelete="RESTRICT"), index=True
    )

    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_utc:   Mapped[datetime] = mapped_column(DateTime(timezone=True))

    local_tz:   Mapped[str] = mapped_column(String(64))                  # e.g. "Europe/Berlin"
    shift_type: Mapped[Optional[str]] = mapped_column(String(64))
    location:   Mapped[Optional[str]] = mapped_column(String(128))
    notes:      Mapped[Optional[str]] = mapped_column(Text)

    # Hash of the provider payload you intend to write (to decide update vs no-op)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))

    provider: Mapped[Optional[str]] = mapped_column(String(32))                    # "gcal", "caldav-icloud", etc.
    provider_event_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    first_synced_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_synced_at_utc:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    status: Mapped[Optional[str]] = mapped_column(EventStatus)
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # Optional lineage if you replace an event due to time change
    replaces_event_uid: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    attachment: Mapped["Attachment"] = relationship(back_populates="events")
    message:    Mapped["Message"]    = relationship()

    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_events_provider_provider_event"),
        CheckConstraint("end_utc > start_utc", name="ck_events_end_after_start"),
        Index("ix_events_start_utc", "start_utc"),
    )
