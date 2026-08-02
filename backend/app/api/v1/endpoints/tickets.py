from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, aliased

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.hrms import Ticket, Employee, TICKET_SLA_HOURS, TICKET_CATEGORIES
from app.models.ticket_comment import TicketComment
from app.schemas.hrms import TicketCreate, TicketUpdate, TicketOut
from app.schemas.ticket_comment import TicketCommentCreate, TicketCommentOut

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _is_breached(ticket: Ticket) -> bool:
    if ticket.sla_due_at is None or ticket.status == "CLOSED":
        return False
    return datetime.utcnow() > ticket.sla_due_at


def _can_view_ticket(user: CurrentUser, ticket: Ticket) -> bool:
    if user.role in ("MANAGER", "ADMIN"):
        return True
    return ticket.created_by == user.id or ticket.assigned_to == user.id


def _to_out(db: Session, ticket: Ticket) -> TicketOut:
    creator = db.query(Employee).filter(Employee.id == ticket.created_by).first()
    assignee = db.query(Employee).filter(Employee.id == ticket.assigned_to).first() if ticket.assigned_to else None
    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        created_by=ticket.created_by,
        created_by_name=creator.name if creator else "Unknown",
        assigned_to=ticket.assigned_to,
        assigned_to_name=assignee.name if assignee else None,
        sla_due_at=ticket.sla_due_at,
        is_breached=_is_breached(ticket),
        created_at=ticket.created_at,
    )


@router.get("/mine")
def list_my_tickets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Ticket)
        .filter(Ticket.created_by == user.id)
        .order_by(Ticket.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": t.id, "title": t.title, "category": t.category, "priority": t.priority,
            "status": t.status, "sla_due_at": t.sla_due_at.isoformat() if t.sla_due_at else None,
            "is_breached": _is_breached(t), "created_at": t.created_at.isoformat(),
        }
        for t in rows
    ]


@router.get("", response_model=list[TicketOut])
def list_all_tickets(
    category: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    breached_only: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manager/admin queue view across every ticket — the counterpart to
    /mine. Managers see everything (not just their own team) because a
    help desk ticket isn't a team-scoped resource like leave or
    attendance; who can *update* one is still gated separately below."""
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view all tickets")

    query = db.query(Ticket)
    if category:
        query = query.filter(Ticket.category == category)
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    rows = query.order_by(Ticket.created_at.desc()).all()

    out = [_to_out(db, t) for t in rows]
    if breached_only:
        out = [o for o in out if o.is_breached]
    return out


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_view_ticket(user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this ticket")
    return _to_out(db, ticket)


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    category = payload.category if payload.category in TICKET_CATEGORIES else "IT"
    sla_hours = TICKET_SLA_HOURS.get(payload.priority, TICKET_SLA_HOURS["MEDIUM"])

    ticket = Ticket(
        created_by=user.id,
        title=payload.title,
        description=payload.description,
        category=category,
        priority=payload.priority,
        status="OPEN",
        sla_due_at=datetime.utcnow() + timedelta(hours=sla_hours),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return _to_out(db, ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update tickets")

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    if payload.status is not None:
        ticket.status = payload.status
    if payload.assigned_to is not None:
        ticket.assigned_to = payload.assigned_to
    if payload.priority is not None:
        # Re-priced SLA: changing priority re-bases the due time from now,
        # rather than leaving a due-date computed against a priority the
        # ticket no longer has.
        ticket.priority = payload.priority
        sla_hours = TICKET_SLA_HOURS.get(payload.priority, TICKET_SLA_HOURS["MEDIUM"])
        ticket.sla_due_at = datetime.utcnow() + timedelta(hours=sla_hours)
    if payload.category is not None and payload.category in TICKET_CATEGORIES:
        ticket.category = payload.category

    db.commit()
    db.refresh(ticket)
    return _to_out(db, ticket)


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentOut])
def list_comments(ticket_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_view_ticket(user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this ticket")

    author = aliased(Employee)
    rows = (
        db.query(TicketComment, author.name)
        .join(author, author.id == TicketComment.employee_id)
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
        .all()
    )
    return [
        TicketCommentOut(
            id=c.id, ticket_id=c.ticket_id, employee_id=c.employee_id,
            employee_name=name, body=c.body, created_at=c.created_at,
        )
        for c, name in rows
    ]


@router.post("/{ticket_id}/comments", response_model=TicketCommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    payload: TicketCommentCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_view_ticket(user, ticket):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to comment on this ticket")
    if not payload.body.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment cannot be empty")

    comment = TicketComment(ticket_id=ticket_id, employee_id=user.id, body=payload.body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return TicketCommentOut(
        id=comment.id, ticket_id=comment.ticket_id, employee_id=comment.employee_id,
        employee_name=user.name, body=comment.body, created_at=comment.created_at,
    )
