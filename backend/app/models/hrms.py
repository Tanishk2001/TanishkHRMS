"""
Existing CB Nest HRMS domain models.

These represent the pre-existing application the AI layer is bolted
onto. Sensitive columns (payroll, bank, PAN, password hash, DOB,
photo blobs) live here deliberately so the SQL guardrails have real
columns to block — see services/ai/sql_guardrails.py FORBIDDEN_COLUMNS.
"""
from datetime import date, datetime

from sqlalchemy import (
    String, Integer, ForeignKey, Date, DateTime, Boolean, Float, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="EMPLOYEE")  # EMPLOYEE/MANAGER/ADMIN
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    job_title: Mapped[str | None] = mapped_column(String(150))
    date_of_birth: Mapped[date | None] = mapped_column(Date)  # sensitive - blocked in SQL agent
    current_salary_usd: Mapped[float | None] = mapped_column(Float)  # sensitive - blocked
    bank_account_number: Mapped[str | None] = mapped_column(String(50))  # sensitive - blocked
    bank_account_name: Mapped[str | None] = mapped_column(String(150))  # sensitive - blocked
    bank_branch: Mapped[str | None] = mapped_column(String(150))  # sensitive - blocked
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))  # sensitive - blocked
    pan_number: Mapped[str | None] = mapped_column(String(20))  # sensitive - blocked
    pan_name: Mapped[str | None] = mapped_column(String(150))  # sensitive - blocked
    pan_dob: Mapped[date | None] = mapped_column(Date)  # sensitive - blocked
    profile_photo_path: Mapped[str | None] = mapped_column(String(255))  # sensitive - blocked
    profile_photo_mime: Mapped[str | None] = mapped_column(String(50))  # sensitive - blocked
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department: Mapped[Department | None] = relationship(back_populates="employees")
    manager: Mapped["Employee"] = relationship(remote_side=[id])


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ONGOING")  # ONGOING/COMPLETED/ON_HOLD
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))


class EmployeeProject(Base):
    __tablename__ = "employee_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    role_on_project: Mapped[str | None] = mapped_column(String(100))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    proficiency: Mapped[str | None] = mapped_column(String(20))  # BEGINNER/INTERMEDIATE/EXPERT


class HRPolicy(Base):
    __tablename__ = "hr_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # LEAVE/ATTENDANCE/WFH/DOCS...
    filename: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(20))  # SICK/CASUAL/EARNED
    balance_days: Mapped[float] = mapped_column(Float, default=0)
    year: Mapped[int] = mapped_column(Integer)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False)
    half_day_period: Mapped[str | None] = mapped_column(String(10))  # AM/PM
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/APPROVED/REJECTED
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


TICKET_SLA_HOURS = {"HIGH": 4, "MEDIUM": 24, "LOW": 72}
TICKET_CATEGORIES = ("HR", "IT", "ADMIN", "FINANCE")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(20), default="IT")  # HR/IT/ADMIN/FINANCE
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW/MEDIUM/HIGH
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN/IN_PROGRESS/CLOSED
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
