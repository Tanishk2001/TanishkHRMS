from datetime import date, datetime

from pydantic import BaseModel


class ExitRequestCreate(BaseModel):
    last_working_day: date
    reason: str | None = None
    employee_id: int | None = None  # admin-only: submit on behalf of someone else


class ExitDecision(BaseModel):
    status: str  # APPROVED / REJECTED


class ChecklistUpdate(BaseModel):
    knowledge_transfer_done: bool | None = None
    exit_interview_done: bool | None = None
    fnf_settled: bool | None = None


class ExitRequestOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    last_working_day: date
    reason: str | None
    status: str
    decided_by: int | None
    decided_at: datetime | None
    knowledge_transfer_done: bool
    exit_interview_done: bool
    fnf_settled: bool
    assets_returned: bool
    completed_at: datetime | None
    created_at: datetime
