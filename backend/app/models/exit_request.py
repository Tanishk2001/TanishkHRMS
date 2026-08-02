"""
Exit Management (Phase 4 addition).

Deliberately a single workflow model rather than one table per stage
(Resignation -> Approval -> Knowledge Transfer -> Asset Return -> Exit
Interview -> F&F Settlement -> Experience Letter from the source doc):
the checklist items are boolean flags on one row, and "assets
returned" is intentionally NOT a stored flag — it's computed live
against AssetAssignment at completion time, so it can't drift out of
sync with reality the way a manually-checked box could.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExitRequest(Base):
    __tablename__ = "exit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    last_working_day: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/APPROVED/REJECTED/COMPLETED
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Offboarding checklist — knowledge_transfer/exit_interview/fnf are
    # manually confirmed by an admin; asset return is never stored here,
    # it's always computed fresh from AssetAssignment.
    knowledge_transfer_done: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_interview_done: Mapped[bool] = mapped_column(Boolean, default=False)
    fnf_settled: Mapped[bool] = mapped_column(Boolean, default=False)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
