from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.models.hrms import Announcement, Employee
from app.schemas.hrms import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


@router.get("")
def list_announcements(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Announcement, Employee.name.label("created_by_name"))
        .join(Employee, Employee.id == Announcement.created_by)
        .order_by(Announcement.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "body": a.body,
            "created_by_name": name,
            "created_at": a.created_at.isoformat(),
        }
        for a, name in rows
    ]


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create announcements")

    announcement = Announcement(created_by=user.id, title=payload.title, body=payload.body)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement
