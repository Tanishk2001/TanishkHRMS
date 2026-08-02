from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str


class ChatActionRequest(BaseModel):
    message: str
    confirm: bool = False
    pending_action: dict | None = None


class PolicySourceOut(BaseModel):
    title: str
    category: str
    filename: str | None = None


class PolicyChatData(BaseModel):
    answer: str
    sources: list[PolicySourceOut]


class SQLChatData(BaseModel):
    answer: str
    sql: str | None = None
    rows: list[dict]


class ActionChatData(BaseModel):
    answer: str
    intent: str | None = None
    status: str
    needs_confirmation: bool = False
    pending_action: dict | None = None


class ChatEnvelope(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


class RouterChatData(BaseModel):
    intent: str
    confidence: float
    reason: str


class AIAuditLogOut(BaseModel):
    id: int
    message: str
    intent: str | None
    tool_name: str | None
    action_status: str | None
    created_at: str


class AIUsageStatsOut(BaseModel):
    total_requests: int
    requests_by_intent: dict[str, int]
    requests_by_tool: dict[str, int]
    failed_permission_attempts: int
    avg_latency_ms: float | None
    rag_no_answer_count: int
    rag_no_answer_rate_pct: float | None
    sql_blocked_count: int
