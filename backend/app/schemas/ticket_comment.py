from datetime import datetime

from pydantic import BaseModel


class TicketCommentCreate(BaseModel):
    body: str


class TicketCommentOut(BaseModel):
    id: int
    ticket_id: int
    employee_id: int
    employee_name: str
    body: str
    created_at: datetime
