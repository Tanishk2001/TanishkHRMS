"""
Help Desk — ticket categories, SLA, and comment threads (Phase 7 addition).

A comment thread is its own table (not a text blob on Ticket) so it can
grow unbounded without rewriting the parent row, and so each comment
carries its own author/timestamp — matching the pattern already used for
AssetAssignment history and the exit-request checklist's separation of
concerns.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
