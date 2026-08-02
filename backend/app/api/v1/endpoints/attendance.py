from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.attendance import AttendanceRecord, LATE_THRESHOLD
from app.models.hrms import Employee
from app.schemas.attendance import AttendanceOut, TodayStatusOut, TeamAttendanceRow

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


def _today_record(db: Session, employee_id: int) -> AttendanceRecord | None:
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == employee_id, AttendanceRecord.work_date == date.today())
        .first()
    )


@router.post("/check-in", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def check_in(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = _today_record(db, user.id)
    if existing and existing.check_in_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in today.")

    now = datetime.now()
    is_late = now.time() > LATE_THRESHOLD
    record = existing or AttendanceRecord(employee_id=user.id, work_date=date.today())
    record.check_in_at = now
    record.status = "LATE" if is_late else "PRESENT"
    if not existing:
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/check-out", response_model=AttendanceOut)
def check_out(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    record = _today_record(db, user.id)
    if record is None or record.check_in_at is None:
        raise HTTPException(status_code=422, detail="You haven't checked in yet today.")
    if record.check_out_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked out today.")

    record.check_out_at = datetime.now()
    db.commit()
    db.refresh(record)
    return record


@router.get("/today", response_model=TodayStatusOut)
def today_status(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    record = _today_record(db, user.id)
    if record is None:
        return TodayStatusOut(checked_in=False, checked_out=False, check_in_at=None, check_out_at=None, status=None)
    return TodayStatusOut(
        checked_in=record.check_in_at is not None,
        checked_out=record.check_out_at is not None,
        check_in_at=record.check_in_at,
        check_out_at=record.check_out_at,
        status=record.status,
    )


@router.get("/me", response_model=list[AttendanceOut])
def my_attendance(
    limit: int = Query(default=14, le=90),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.employee_id == user.id)
        .order_by(AttendanceRecord.work_date.desc())
        .limit(limit)
        .all()
    )


@router.get("/team", response_model=list[TeamAttendanceRow])
def team_attendance(
    for_date: date = Query(default_factory=date.today),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view team attendance.")

    query = (
        db.query(AttendanceRecord, Employee.name)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .filter(AttendanceRecord.work_date == for_date)
    )
    if user.role == "MANAGER":
        query = query.filter(Employee.manager_id == user.id)

    rows = query.all()
    return [
        TeamAttendanceRow(
            employee_id=r.employee_id,
            employee_name=name,
            work_date=r.work_date,
            check_in_at=r.check_in_at,
            check_out_at=r.check_out_at,
            status=r.status,
        )
        for r, name in rows
    ]
