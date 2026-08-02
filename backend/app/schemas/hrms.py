from datetime import date, datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class EmployeeCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "EMPLOYEE"  # EMPLOYEE/MANAGER/ADMIN
    department_id: int | None = None
    manager_id: int | None = None
    job_title: str | None = None


class EmployeeOut(BaseModel):
    id: int
    name: str
    job_title: str | None
    role: str
    department: str | None


class DepartmentOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_period: str | None = None
    reason: str | None = None


class LeaveRequestUpdate(BaseModel):
    status: str  # APPROVED / REJECTED


class LeaveRequestOut(BaseModel):
    id: int
    leave_type: str
    start_date: date
    end_date: date
    status: str

    class Config:
        from_attributes = True


class LeaveBalanceOut(BaseModel):
    leave_type: str
    balance_days: float
    year: int

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str
    description: str | None = None
    category: str = "IT"
    priority: str = "MEDIUM"


class TicketUpdate(BaseModel):
    status: str | None = None
    assigned_to: int | None = None
    priority: str | None = None
    category: str | None = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str | None
    category: str
    status: str
    priority: str
    created_by: int
    created_by_name: str
    assigned_to: int | None
    assigned_to_name: str | None
    sla_due_at: datetime | None
    is_breached: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementCreate(BaseModel):
    title: str
    body: str


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str

    class Config:
        from_attributes = True


class ProjectAssignmentCreate(BaseModel):
    project_id: int
    role_on_project: str | None = None
