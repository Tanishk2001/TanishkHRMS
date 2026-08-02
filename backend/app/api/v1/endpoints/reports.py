from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.attendance import AttendanceRecord
from app.models.hrms import Employee, Department, LeaveRequest, Ticket
from app.schemas.reports import (
    HeadcountReport, HeadcountByDepartment,
    LeaveTrendsReport, LeaveTypeBreakdown,
    AttendanceTrendsReport, AttendanceDayBreakdown,
    TicketsReport, TicketStatusBreakdown, TicketPriorityBreakdown, TicketCategoryBreakdown,
)
from app.services.ai import permissions

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _require_analytics_access(user: CurrentUser) -> None:
    if not permissions.can_view_analytics(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view analytics.")


@router.get("/headcount", response_model=HeadcountReport)
def headcount_report(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_analytics_access(user)

    total_active = db.query(func.count(Employee.id)).filter(Employee.is_active == True).scalar()  # noqa: E712
    total_inactive = db.query(func.count(Employee.id)).filter(Employee.is_active == False).scalar()  # noqa: E712

    dept_rows = (
        db.query(Department.name, func.count(Employee.id))
        .outerjoin(Employee, (Employee.department_id == Department.id) & (Employee.is_active == True))  # noqa: E712
        .group_by(Department.name)
        .all()
    )
    role_rows = (
        db.query(Employee.role, func.count(Employee.id))
        .filter(Employee.is_active == True)  # noqa: E712
        .group_by(Employee.role)
        .all()
    )

    return HeadcountReport(
        total_active=total_active or 0,
        total_inactive=total_inactive or 0,
        by_department=[HeadcountByDepartment(department=name, headcount=count) for name, count in dept_rows],
        by_role={role: count for role, count in role_rows},
    )


@router.get("/leave-trends", response_model=LeaveTrendsReport)
def leave_trends_report(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_analytics_access(user)

    rows = (
        db.query(LeaveRequest.leave_type, LeaveRequest.status, func.count(LeaveRequest.id))
        .group_by(LeaveRequest.leave_type, LeaveRequest.status)
        .all()
    )
    by_type: dict[str, dict[str, int]] = {}
    for leave_type, status_, count in rows:
        by_type.setdefault(leave_type, {"APPROVED": 0, "PENDING": 0, "REJECTED": 0})
        by_type[leave_type][status_] = count

    cutoff = date.today() - timedelta(days=90)
    total_recent = (
        db.query(func.count(LeaveRequest.id))
        .filter(LeaveRequest.created_at >= cutoff)
        .scalar()
    )

    return LeaveTrendsReport(
        by_type=[
            LeaveTypeBreakdown(
                leave_type=lt,
                approved=counts["APPROVED"],
                pending=counts["PENDING"],
                rejected=counts["REJECTED"],
            )
            for lt, counts in by_type.items()
        ],
        total_requests_last_90_days=total_recent or 0,
    )


@router.get("/attendance-trends", response_model=AttendanceTrendsReport)
def attendance_trends_report(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_analytics_access(user)

    cutoff = date.today() - timedelta(days=14)
    rows = (
        db.query(AttendanceRecord.work_date, AttendanceRecord.status, func.count(AttendanceRecord.id))
        .filter(AttendanceRecord.work_date >= cutoff)
        .group_by(AttendanceRecord.work_date, AttendanceRecord.status)
        .order_by(AttendanceRecord.work_date)
        .all()
    )
    by_day: dict[str, dict[str, int]] = {}
    for work_date, status_, count in rows:
        key = work_date.isoformat()
        by_day.setdefault(key, {"PRESENT": 0, "LATE": 0, "ABSENT": 0})
        by_day[key][status_] = count

    total_present = sum(d["PRESENT"] for d in by_day.values())
    total_late = sum(d["LATE"] for d in by_day.values())
    denom = total_present + total_late
    late_rate = round((total_late / denom) * 100, 1) if denom else 0.0

    return AttendanceTrendsReport(
        last_14_days=[
            AttendanceDayBreakdown(work_date=day, present=c["PRESENT"], late=c["LATE"], absent=c["ABSENT"])
            for day, c in sorted(by_day.items())
        ],
        late_rate_pct=late_rate,
    )


@router.get("/tickets", response_model=TicketsReport)
def tickets_report(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_analytics_access(user)

    status_rows = db.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    priority_rows = db.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
    category_rows = db.query(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category).all()
    total_open = db.query(func.count(Ticket.id)).filter(Ticket.status == "OPEN").scalar()
    total_breached = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.status != "CLOSED", Ticket.sla_due_at.isnot(None), Ticket.sla_due_at < datetime.utcnow())
        .scalar()
    )

    return TicketsReport(
        by_status=[TicketStatusBreakdown(status=s, count=c) for s, c in status_rows],
        by_priority=[TicketPriorityBreakdown(priority=p, count=c) for p, c in priority_rows],
        by_category=[TicketCategoryBreakdown(category=cat, count=c) for cat, c in category_rows],
        total_open=total_open or 0,
        total_breached=total_breached or 0,
    )
