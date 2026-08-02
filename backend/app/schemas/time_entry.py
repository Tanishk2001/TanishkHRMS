from datetime import date

from pydantic import BaseModel


class TimeEntryCreate(BaseModel):
    project_id: int
    work_date: date
    hours: float
    billable: bool = True
    description: str | None = None


class TimeEntryOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    work_date: date
    hours: float
    billable: bool
    description: str | None


class TeamTimeEntryOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    project_id: int
    project_name: str
    work_date: date
    hours: float
    billable: bool
