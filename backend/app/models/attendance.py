"""
Attendance Management (Phase 1 addition).

Deliberately scoped to web check-in/check-out — no GPS/geofencing/
biometric/face-recognition/RFID, which need hardware or ML integrations
this project doesn't have. The late-arrival threshold (10:15 AM) is
not a magic number: it matches the "Attendance & Late Login Policy"
already seeded in hr_policies, so the Policy RAG assistant's answer
and this table's actual behavior agree with each other.
"""
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

LATE_THRESHOLD = time(10, 15)  # matches hr_policies: "Attendance & Late Login Policy"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")  # PRESENT/LATE/ABSENT
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
