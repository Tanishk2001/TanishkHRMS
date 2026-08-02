from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.asset import Asset, AssetAssignment
from app.models.hrms import Employee
from app.schemas.asset import (
    AssetCreate, AssetOut, AssetWithHolder, IssueAssetRequest, ReturnAssetRequest, AssetAssignmentOut,
)

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


def _require_manage_assets(user: CurrentUser) -> None:
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage assets.")


def _active_assignment(db: Session, asset_id: int) -> AssetAssignment | None:
    return (
        db.query(AssetAssignment)
        .filter(AssetAssignment.asset_id == asset_id, AssetAssignment.returned_at.is_(None))
        .first()
    )


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can add new assets.")

    if db.query(Asset).filter(Asset.asset_tag == payload.asset_tag).first():
        raise HTTPException(status_code=422, detail="An asset with this tag already exists.")

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetWithHolder])
def list_assets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_manage_assets(user)

    assets = db.query(Asset).order_by(Asset.category, Asset.name).all()
    results = []
    for a in assets:
        active = _active_assignment(db, a.id)
        holder_name = None
        if active:
            holder = db.query(Employee).filter(Employee.id == active.employee_id).first()
            holder_name = holder.name if holder else None
        results.append(AssetWithHolder(**AssetOut.model_validate(a).model_dump(), current_holder_name=holder_name))
    return results


@router.get("/me", response_model=list[AssetOut])
def my_assets(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Asset)
        .join(AssetAssignment, AssetAssignment.asset_id == Asset.id)
        .filter(AssetAssignment.employee_id == user.id, AssetAssignment.returned_at.is_(None))
        .all()
    )
    return rows


@router.get("/{asset_id}/history", response_model=list[AssetAssignmentOut])
def asset_history(asset_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_manage_assets(user)

    rows = (
        db.query(AssetAssignment, Employee.name)
        .join(Employee, Employee.id == AssetAssignment.employee_id)
        .filter(AssetAssignment.asset_id == asset_id)
        .order_by(AssetAssignment.issued_at.desc())
        .all()
    )
    return [
        AssetAssignmentOut(
            id=a.id, asset_id=a.asset_id, employee_id=a.employee_id, employee_name=name,
            issued_at=a.issued_at, returned_at=a.returned_at,
            condition_on_issue=a.condition_on_issue, condition_on_return=a.condition_on_return, notes=a.notes,
        )
        for a, name in rows
    ]


@router.post("/{asset_id}/issue", response_model=AssetOut)
def issue_asset(
    asset_id: int,
    payload: IssueAssetRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_manage_assets(user)

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.status != "AVAILABLE":
        raise HTTPException(status_code=422, detail=f"Asset is currently {asset.status.lower()}, not available to issue.")

    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    assignment = AssetAssignment(
        asset_id=asset.id,
        employee_id=payload.employee_id,
        issued_by=user.id,
        condition_on_issue=payload.condition_on_issue,
        notes=payload.notes,
    )
    asset.status = "ASSIGNED"
    db.add(assignment)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/{asset_id}/return", response_model=AssetOut)
def return_asset(
    asset_id: int,
    payload: ReturnAssetRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_manage_assets(user)

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    assignment = _active_assignment(db, asset_id)
    if assignment is None:
        raise HTTPException(status_code=422, detail="This asset isn't currently issued to anyone.")

    assignment.returned_at = datetime.now()
    assignment.condition_on_return = payload.condition_on_return
    if payload.notes:
        assignment.notes = f"{assignment.notes or ''}\n[return] {payload.notes}".strip()

    asset.status = "IN_REPAIR" if payload.condition_on_return == "DAMAGED" else "AVAILABLE"
    db.commit()
    db.refresh(asset)
    return asset
