from pydantic import BaseModel


class HeadcountByDepartment(BaseModel):
    department: str
    headcount: int


class HeadcountReport(BaseModel):
    total_active: int
    total_inactive: int
    by_department: list[HeadcountByDepartment]
    by_role: dict[str, int]


class LeaveTypeBreakdown(BaseModel):
    leave_type: str
    approved: int
    pending: int
    rejected: int


class LeaveTrendsReport(BaseModel):
    by_type: list[LeaveTypeBreakdown]
    total_requests_last_90_days: int


class AttendanceDayBreakdown(BaseModel):
    work_date: str
    present: int
    late: int
    absent: int


class AttendanceTrendsReport(BaseModel):
    last_14_days: list[AttendanceDayBreakdown]
    late_rate_pct: float


class TicketStatusBreakdown(BaseModel):
    status: str
    count: int


class TicketPriorityBreakdown(BaseModel):
    priority: str
    count: int


class TicketCategoryBreakdown(BaseModel):
    category: str
    count: int


class TicketsReport(BaseModel):
    by_status: list[TicketStatusBreakdown]
    by_priority: list[TicketPriorityBreakdown]
    by_category: list[TicketCategoryBreakdown]
    total_open: int
    total_breached: int
