from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.engagement import Poll, PollOption, PollVote, Kudos
from app.models.hrms import Employee
from app.schemas.engagement import PollCreate, PollOut, PollOptionResult, VoteRequest, KudosCreate, KudosOut
from app.services.ai import permissions

router = APIRouter(prefix="/api/v1", tags=["engagement"])


def _to_poll_out(db: Session, poll: Poll, creator_name: str, user_id: int) -> PollOut:
    options = db.query(PollOption).filter(PollOption.poll_id == poll.id).order_by(PollOption.sort_order).all()
    vote_counts = {
        opt.id: db.query(PollVote).filter(PollVote.option_id == opt.id).count() for opt in options
    }
    my_vote = db.query(PollVote).filter(PollVote.poll_id == poll.id, PollVote.employee_id == user_id).first()

    return PollOut(
        id=poll.id, question=poll.question, status=poll.status,
        created_by_name=creator_name, created_at=poll.created_at,
        options=[PollOptionResult(id=o.id, option_text=o.option_text, vote_count=vote_counts[o.id]) for o in options],
        total_votes=sum(vote_counts.values()),
        my_vote_option_id=my_vote.option_id if my_vote else None,
    )


@router.post("/polls", response_model=PollOut, status_code=status.HTTP_201_CREATED)
def create_poll(payload: PollCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not permissions.can_manage_polls(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create polls.")

    poll = Poll(question=payload.question, created_by=user.id)
    db.add(poll)
    db.flush()
    for i, text in enumerate(payload.options):
        db.add(PollOption(poll_id=poll.id, option_text=text, sort_order=i))
    db.commit()
    db.refresh(poll)
    return _to_poll_out(db, poll, user.name, user.id)


@router.get("/polls", response_model=list[PollOut])
def list_polls(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Poll, Employee.name).join(Employee, Employee.id == Poll.created_by).order_by(Poll.created_at.desc()).all()
    return [_to_poll_out(db, poll, name, user.id) for poll, name in rows]


@router.post("/polls/{poll_id}/vote", response_model=PollOut)
def vote_poll(poll_id: int, payload: VoteRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found.")
    if poll.status != "OPEN":
        raise HTTPException(status_code=422, detail="This poll is closed.")

    option = db.query(PollOption).filter(PollOption.id == payload.option_id, PollOption.poll_id == poll_id).first()
    if option is None:
        raise HTTPException(status_code=422, detail="That option doesn't belong to this poll.")

    existing = db.query(PollVote).filter(PollVote.poll_id == poll_id, PollVote.employee_id == user.id).first()
    if existing:
        raise HTTPException(status_code=422, detail="You've already voted in this poll.")

    db.add(PollVote(poll_id=poll_id, option_id=payload.option_id, employee_id=user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=422, detail="You've already voted in this poll.")

    creator = db.query(Employee).filter(Employee.id == poll.created_by).first()
    return _to_poll_out(db, poll, creator.name, user.id)


@router.post("/polls/{poll_id}/close", response_model=PollOut)
def close_poll(poll_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not permissions.can_manage_polls(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to close polls.")

    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found.")
    if poll.status == "CLOSED":
        raise HTTPException(status_code=422, detail="This poll is already closed.")

    poll.status = "CLOSED"
    db.commit()
    db.refresh(poll)
    creator = db.query(Employee).filter(Employee.id == poll.created_by).first()
    return _to_poll_out(db, poll, creator.name, user.id)


@router.post("/kudos", response_model=KudosOut, status_code=status.HTTP_201_CREATED)
def give_kudos(payload: KudosCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.to_employee_id == user.id:
        raise HTTPException(status_code=422, detail="You can't give kudos to yourself.")

    recipient = db.query(Employee).filter(Employee.id == payload.to_employee_id).first()
    if recipient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    kudos = Kudos(from_employee_id=user.id, to_employee_id=payload.to_employee_id,
                  category=payload.category, message=payload.message)
    db.add(kudos)
    db.commit()
    db.refresh(kudos)

    return KudosOut(
        id=kudos.id, from_employee_name=user.name, to_employee_name=recipient.name,
        category=kudos.category, message=kudos.message, created_at=kudos.created_at,
    )


@router.get("/kudos", response_model=list[KudosOut])
def list_kudos(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    from_emp = aliased(Employee)
    to_emp = aliased(Employee)

    rows = (
        db.query(Kudos, from_emp.name, to_emp.name)
        .join(from_emp, from_emp.id == Kudos.from_employee_id)
        .join(to_emp, to_emp.id == Kudos.to_employee_id)
        .order_by(Kudos.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        KudosOut(id=k.id, from_employee_name=fn, to_employee_name=tn, category=k.category,
                 message=k.message, created_at=k.created_at)
        for k, fn, tn in rows
    ]
