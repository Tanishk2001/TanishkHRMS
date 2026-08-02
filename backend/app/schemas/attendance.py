from datetime import date, datetime

from pydantic import BaseModel


class AttendanceOut(BaseModel):
    id: int
    work_date: date
    check_in_at: datetime | None
    check_out_at: datetime | None
    status: str

    class Config:
        from_attributes = True


class TodayStatusOut(BaseModel):
    checked_in: bool
    checked_out: bool
    check_in_at: datetime | None
    check_out_at: datetime | None
    status: str | None


class TeamAttendanceRow(BaseModel):
    employee_id: int
    employee_name: str
    work_date: date
    check_in_at: datetime | None
    check_out_at: datetime | None
    status: str
