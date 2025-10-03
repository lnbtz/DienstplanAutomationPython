from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import (
     Enum, 
    String, Text, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shiftbot.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attachment import Attachment

MessageStatus = Enum(
    "processed", "parse_error", "skipped", "failed_upsert",
    name="message_status",
)


class Message(Base):
    """
    One row per relevant email message (source provenance).
    """
    __tablename__ = "messages"

    # RFC 5322 Message-Id (string); good idempotency anchor if preserved.
    msg_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    from_addr: Mapped[Optional[str]] = mapped_column(String(255))
    subject:   Mapped[Optional[str]] = mapped_column(String(512))
    provider:  Mapped[Optional[str]] = mapped_column(String(32))   # e.g., "imap", "gmail"

    received_at_utc:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    status: Mapped[Optional[str]] = mapped_column(MessageStatus)
    notes:  Mapped[Optional[str]] = mapped_column(Text)

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
    
