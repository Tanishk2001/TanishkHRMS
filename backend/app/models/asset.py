"""
Asset Management (Phase 3 addition).

An Asset can be reassigned across employees over its lifetime, so
assignment history lives in its own table rather than a single
"assigned_to" column on Asset — AssetAssignment rows with
returned_at IS NULL represent the current holder; closed rows are
history. Asset.status is a denormalized convenience field kept in
sync by the endpoint logic (never trust it alone for "who has this
asset right now" — join on the open assignment for that).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)  # LAPTOP/MONITOR/MOUSE/MOBILE/SIM/LICENSE/ACCESSORY
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. "MacBook Pro 14 M3"
    serial_number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE")  # AVAILABLE/ASSIGNED/IN_REPAIR/RETIRED
    purchase_date: Mapped[date | None] = mapped_column(Date)
    warranty_expiry: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    issued_by: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    condition_on_issue: Mapped[str | None] = mapped_column(String(20))  # NEW/GOOD/FAIR/DAMAGED
    condition_on_return: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
