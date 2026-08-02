from datetime import datetime

from pydantic import BaseModel, field_validator


class PollCreate(BaseModel):
    question: str
    options: list[str]

    @field_validator("options")
    @classmethod
    def at_least_two_options(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("A poll needs at least two options.")
        return v


class PollOptionResult(BaseModel):
    id: int
    option_text: str
    vote_count: int


class PollOut(BaseModel):
    id: int
    question: str
    status: str
    created_by_name: str
    created_at: datetime
    options: list[PollOptionResult]
    total_votes: int
    my_vote_option_id: int | None


class VoteRequest(BaseModel):
    option_id: int


class KudosCreate(BaseModel):
    to_employee_id: int
    category: str = "TEAMWORK"
    message: str


class KudosOut(BaseModel):
    id: int
    from_employee_name: str
    to_employee_name: str
    category: str
    message: str
    created_at: datetime
