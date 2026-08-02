from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.hrms import Employee

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class CurrentUser:
    """Lightweight identity object threaded through the AI layer."""

    def __init__(self, id: int, email: str, role: str, name: str, department_id: int | None,
                 manager_id: int | None, access_token: str):
        self.id = id
        self.email = email
        self.role = role  # EMPLOYEE / MANAGER / ADMIN
        self.name = name
        self.department_id = department_id
        self.manager_id = manager_id
        self.access_token = access_token  # forwarded to internal API tool calls


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    employee = db.query(Employee).filter(Employee.email == email).first()
    if employee is None or not employee.is_active:
        raise credentials_exception

    return CurrentUser(
        id=employee.id,
        email=employee.email,
        role=employee.role,
        name=employee.name,
        department_id=employee.department_id,
        manager_id=employee.manager_id,
        access_token=token,
    )
