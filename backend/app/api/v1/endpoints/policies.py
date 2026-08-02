from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.hrms import HRPolicy

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.get("")
def list_policies(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(HRPolicy).order_by(HRPolicy.category, HRPolicy.title).all()
    return [
        {"id": p.id, "title": p.title, "category": p.category, "filename": p.filename, "content": p.content}
        for p in rows
    ]
