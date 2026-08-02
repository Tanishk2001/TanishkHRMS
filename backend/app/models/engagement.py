"""
Employee Engagement — Polls & Kudos (Phase 5 addition).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="OPEN")  # OPEN/CLOSED
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(String(150), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class PollVote(Base):
    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "employee_id", name="uq_poll_votes_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"), nullable=False)
    option_id: Mapped[int] = mapped_column(ForeignKey("poll_options.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    voted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Kudos(Base):
    __tablename__ = "kudos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    to_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), default="TEAMWORK")  # TEAMWORK/INNOVATION/LEADERSHIP/CUSTOMER_FOCUS/OTHER
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
