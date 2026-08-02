from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.asset import AssetAssignment
from app.models.exit_request import ExitRequest
from app.models.hrms import Employee
from app.schemas.exit_request import ExitRequestCreate, ExitDecision, ChecklistUpdate, ExitRequestOut
from app.services.ai import permissions

router = APIRouter(prefix="/api/v1/exits", tags=["exits"])


def _assets_returned(db: Session, employee_id: int) -> bool:
    """True iff the employee currently holds no assets — computed
    live, never stored, so it can't go stale."""
    active = (
        db.query(AssetAssignment)
        .filter(AssetAssignment.employee_id == employee_id, AssetAssignment.returned_at.is_(None))
        .first()
    )
    return active is None


def _to_out(db: Session, req: ExitRequest, employee_name: str) -> ExitRequestOut:
    return ExitRequestOut(
        id=req.id, employee_id=req.employee_id, employee_name=employee_name,
        last_working_day=req.last_working_day, reason=req.reason, status=req.status,
        decided_by=req.decided_by, decided_at=req.decided_at,
        knowledge_transfer_done=req.knowledge_transfer_done,
        exit_interview_done=req.exit_interview_done, fnf_settled=req.fnf_settled,
        assets_returned=_assets_returned(db, req.employee_id),
        completed_at=req.completed_at, created_at=req.created_at,
    )


@router.post("", response_model=ExitRequestOut, status_code=status.HTTP_201_CREATED)
def submit_resignation(
    payload: ExitRequestCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_employee_id = user.id
    if payload.employee_id is not None and payload.employee_id != user.id:
        if user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                 detail="Only an admin can submit a resignation on someone else's behalf.")
        target_employee_id = payload.employee_id

    existing_open = (
        db.query(ExitRequest)
        .filter(ExitRequest.employee_id == target_employee_id, ExitRequest.status.in_(("PENDING", "APPROVED")))
        .first()
    )
    if existing_open:
        raise HTTPException(status_code=422, detail="There is already an open exit request for this employee.")

    req = ExitRequest(
        employee_id=target_employee_id, requested_by=user.id,
        last_working_day=payload.last_working_day, reason=payload.reason,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    employee = db.query(Employee).filter(Employee.id == target_employee_id).first()
    return _to_out(db, req, employee.name)


@router.get("/me", response_model=list[ExitRequestOut])
def my_exit_requests(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ExitRequest).filter(ExitRequest.employee_id == user.id).order_by(ExitRequest.created_at.desc()).all()
    return [_to_out(db, r, user.name) for r in rows]


@router.get("", response_model=list[ExitRequestOut])
def list_exit_requests(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view exit requests.")

    query = db.query(ExitRequest, Employee).join(Employee, Employee.id == ExitRequest.employee_id)
    if user.role == "MANAGER":
        query = query.filter(Employee.manager_id == user.id)
    rows = query.order_by(ExitRequest.created_at.desc()).all()
    return [_to_out(db, r, emp.name) for r, emp in rows]


@router.patch("/{exit_id}/decision", response_model=ExitRequestOut)
def decide_exit_request(
    exit_id: int,
    payload: ExitDecision,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit request not found.")

    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    if not permissions.can_decide_exit_request(user, employee.manager_id if employee else None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to decide this request.")
    if req.status != "PENDING":
        raise HTTPException(status_code=422, detail=f"This request is already {req.status.lower()}.")
    if payload.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=422, detail="status must be APPROVED or REJECTED")

    req.status = payload.status
    req.decided_by = user.id
    req.decided_at = datetime.now()
    db.commit()
    db.refresh(req)
    return _to_out(db, req, employee.name)


@router.patch("/{exit_id}/checklist", response_model=ExitRequestOut)
def update_checklist(
    exit_id: int,
    payload: ChecklistUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not permissions.can_manage_exit_checklist_and_completion(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage the offboarding checklist.")

    req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit request not found.")
    if req.status != "APPROVED":
        raise HTTPException(status_code=422, detail="Checklist can only be updated on an approved exit request.")

    if payload.knowledge_transfer_done is not None:
        req.knowledge_transfer_done = payload.knowledge_transfer_done
    if payload.exit_interview_done is not None:
        req.exit_interview_done = payload.exit_interview_done
    if payload.fnf_settled is not None:
        req.fnf_settled = payload.fnf_settled
    db.commit()
    db.refresh(req)

    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    return _to_out(db, req, employee.name)


@router.post("/{exit_id}/complete", response_model=ExitRequestOut)
def complete_exit(exit_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not permissions.can_manage_exit_checklist_and_completion(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to complete offboarding.")

    req = db.query(ExitRequest).filter(ExitRequest.id == exit_id).first()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exit request not found.")
    if req.status != "APPROVED":
        raise HTTPException(status_code=422, detail="Only an approved exit request can be completed.")

    missing = []
    if not req.knowledge_transfer_done:
        missing.append("knowledge transfer")
    if not req.exit_interview_done:
        missing.append("exit interview")
    if not req.fnf_settled:
        missing.append("full & final settlement")
    if not _assets_returned(db, req.employee_id):
        missing.append("asset return")
    if missing:
        raise HTTPException(status_code=422, detail=f"Cannot complete offboarding — still pending: {', '.join(missing)}.")

    employee = db.query(Employee).filter(Employee.id == req.employee_id).first()
    employee.is_active = False
    req.status = "COMPLETED"
    req.completed_at = datetime.now()
    db.commit()
    db.refresh(req)
    return _to_out(db, req, employee.name)
