from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.hrms import Employee, Project, EmployeeProject
from app.models.time_entry import TimeEntry
from app.schemas.time_entry import TimeEntryCreate, TimeEntryOut, TeamTimeEntryOut
from app.services.ai import permissions

router = APIRouter(prefix="/api/v1/time-entries", tags=["time-tracking"])

MAX_DAILY_HOURS = 24.0


@router.post("", response_model=TimeEntryOut, status_code=status.HTTP_201_CREATED)
def log_time(payload: TimeEntryCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.hours <= 0:
        raise HTTPException(status_code=422, detail="Hours must be greater than 0.")
    if payload.hours > MAX_DAILY_HOURS:
        raise HTTPException(status_code=422, detail=f"A single entry can't exceed {MAX_DAILY_HOURS} hours.")

    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    assignment = (
        db.query(EmployeeProject)
        .filter(EmployeeProject.employee_id == user.id, EmployeeProject.project_id == payload.project_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=422, detail="You can only log time against a project you're assigned to.")

    existing_total = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0.0))
        .filter(TimeEntry.employee_id == user.id, TimeEntry.work_date == payload.work_date)
        .scalar()
    )
    if existing_total + payload.hours > MAX_DAILY_HOURS:
        raise HTTPException(
            status_code=422,
            detail=f"That would put you at {existing_total + payload.hours:.1f}h logged for {payload.work_date} — max is {MAX_DAILY_HOURS}h/day.",
        )

    entry = TimeEntry(
        employee_id=user.id, project_id=payload.project_id, work_date=payload.work_date,
        hours=payload.hours, billable=payload.billable, description=payload.description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return TimeEntryOut(id=entry.id, project_id=entry.project_id, project_name=project.name,
                         work_date=entry.work_date, hours=entry.hours, billable=entry.billable,
                         description=entry.description)


@router.get("/me", response_model=list[TimeEntryOut])
def my_time_entries(
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=14)),
    end: date = Query(default_factory=date.today),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TimeEntry, Project.name)
        .join(Project, Project.id == TimeEntry.project_id)
        .filter(TimeEntry.employee_id == user.id, TimeEntry.work_date >= start, TimeEntry.work_date <= end)
        .order_by(TimeEntry.work_date.desc())
        .all()
    )
    return [
        TimeEntryOut(id=e.id, project_id=e.project_id, project_name=name, work_date=e.work_date,
                     hours=e.hours, billable=e.billable, description=e.description)
        for e, name in rows
    ]


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_time_entry(entry_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found.")
    if entry.employee_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own time entries.")

    db.delete(entry)
    db.commit()


@router.get("/team", response_model=list[TeamTimeEntryOut])
def team_time_entries(
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    end: date = Query(default_factory=date.today),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not permissions.can_view_team_time_entries(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view team time entries.")

    query = (
        db.query(TimeEntry, Employee.name, Project.name)
        .join(Employee, Employee.id == TimeEntry.employee_id)
        .join(Project, Project.id == TimeEntry.project_id)
        .filter(TimeEntry.work_date >= start, TimeEntry.work_date <= end)
    )
    if user.role == "MANAGER":
        query = query.filter(Employee.manager_id == user.id)

    rows = query.order_by(TimeEntry.work_date.desc()).all()
    return [
        TeamTimeEntryOut(id=e.id, employee_id=e.employee_id, employee_name=emp_name,
                          project_id=e.project_id, project_name=proj_name,
                          work_date=e.work_date, hours=e.hours, billable=e.billable)
        for e, emp_name, proj_name in rows
    ]
