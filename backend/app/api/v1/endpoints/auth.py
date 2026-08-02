from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.db.database import get_db
from app.models.hrms import Employee
from app.schemas.hrms import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.email == payload.email).first()
    if not employee or not verify_password(payload.password, employee.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(subject=employee.email, role=employee.role)
    return TokenResponse(access_token=token, role=employee.role)
