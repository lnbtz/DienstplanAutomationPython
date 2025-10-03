from __future__ import annotations
from shiftbot.db.base import Base
from typing import Optional
from sqlalchemy import (
    Boolean, ForeignKey, 
    Integer, String
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .message import Message
    from .event import Event
class Attachment(Base):
    """
    The PDF shift plan Shifts are extracted from.
    """
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    msg_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("messages.msg_id", ondelete="RESTRICT"), index=True
    )

    filename:  Mapped[Optional[str]] = mapped_column(String(512))
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)

    # Strong idempotency key across resends/renames
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    validated:   Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stored_path: Mapped[Optional[str]] = mapped_column(String(1024))

    message: Mapped["Message"] = relationship(back_populates="attachments")

    events: Mapped[list["Event"]] = relationship(
        back_populates="attachment", cascade="all, delete-orphan"
    )
