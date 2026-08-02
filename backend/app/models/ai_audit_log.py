from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AIAuditLog(Base):
    """
    One row per AI interaction. Never store secrets, full JWTs,
    passwords, bank details, or PAN numbers here — only IDs, intent,
    and status metadata.
    """
    __tablename__ = "ai_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50))
    tool_name: Mapped[str | None] = mapped_column(String(100))
    action_status: Mapped[str | None] = mapped_column(String(30))  # SUCCESS/DENIED/ERROR
    records_accessed: Mapped[str | None] = mapped_column(Text)  # comma-separated IDs, never raw PII
    latency_ms: Mapped[int | None] = mapped_column(Integer)  # wall-clock time for the request, for the usage dashboard
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
