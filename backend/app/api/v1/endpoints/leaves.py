from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.hrms import LeaveRequest, LeaveBalance
from app.schemas.hrms import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestOut, LeaveBalanceOut

router = APIRouter(prefix="/api/v1/leaves", tags=["leaves"])


@router.get("/balance", response_model=list[LeaveBalanceOut])
def get_my_leave_balance(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(LeaveBalance).filter(LeaveBalance.employee_id == user.id).all()


@router.post("/requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    payload: LeaveRequestCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --- business validation lives here, not in the AI layer ---
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="end_date cannot be before start_date")
    if payload.start_date < date.today():
        raise HTTPException(status_code=422, detail="Cannot request leave in the past")

    requested_days = (payload.end_date - payload.start_date).days + 1
    if payload.is_half_day:
        requested_days = 0.5

    balance = (
        db.query(LeaveBalance)
        .filter(LeaveBalance.employee_id == user.id, LeaveBalance.leave_type == payload.leave_type)
        .first()
    )
    if balance is None or balance.balance_days < requested_days:
        raise HTTPException(status_code=422, detail="Insufficient leave balance for this request")

    leave = LeaveRequest(
        employee_id=user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_half_day=payload.is_half_day,
        half_day_period=payload.half_day_period,
        reason=payload.reason,
        status="PENDING",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.patch("/requests/{request_id}", response_model=LeaveRequestOut)
def update_leave_request_status(
    request_id: int,
    payload: LeaveRequestUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to approve/reject leave")

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if leave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    if payload.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=422, detail="status must be APPROVED or REJECTED")

    leave.status = payload.status
    leave.approved_by = user.id
    db.commit()
    db.refresh(leave)
    return leave
