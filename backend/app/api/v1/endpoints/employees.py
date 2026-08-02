from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser, hash_password
from app.db.database import get_db
from app.models.hrms import EmployeeProject, Employee, Project, Department
from app.schemas.hrms import ProjectAssignmentCreate, EmployeeCreate, EmployeeOut, DepartmentOut

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])

VALID_ROLES = ("EMPLOYEE", "MANAGER", "ADMIN")


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Populates the department picker on the Add Employee form — plain
    id/name pairs, nothing sensitive, so any authenticated role can read it."""
    return db.query(Department).order_by(Department.name).all()


@router.get("")
def list_employees(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Directory listing — name/title/department only, never salary/bank/PAN/etc.
    Visible to every authenticated role, same as clicking through to an
    Employees tab in the real app would be."""
    rows = (
        db.query(Employee.id, Employee.name, Employee.job_title, Employee.role, Department.name.label("department"))
        .outerjoin(Department, Department.id == Employee.department_id)
        .filter(Employee.is_active == True)  # noqa: E712
        .order_by(Employee.name)
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "job_title": r.job_title, "role": r.role, "department": r.department}
        for r in rows
    ]


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a new employee record (Core HR). Admin-only, same pattern as
    asset creation — an org chart change is exactly the kind of action
    that shouldn't be self-service for managers, even ones who can
    approve leave/exits for their own team."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can add new employees.")

    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")

    if db.query(Employee).filter(Employee.email == payload.email).first():
        raise HTTPException(status_code=422, detail="An employee with this email already exists.")

    if payload.department_id is not None:
        if not db.query(Department).filter(Department.id == payload.department_id).first():
            raise HTTPException(status_code=404, detail="Department not found.")

    if payload.manager_id is not None:
        if not db.query(Employee).filter(Employee.id == payload.manager_id).first():
            raise HTTPException(status_code=404, detail="Manager not found.")

    employee = Employee(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        job_title=payload.job_title,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    department_name = None
    if employee.department_id:
        dept = db.query(Department).filter(Department.id == employee.department_id).first()
        department_name = dept.name if dept else None

    return EmployeeOut(
        id=employee.id, name=employee.name, job_title=employee.job_title,
        role=employee.role, department=department_name,
    )


@router.get("/me/projects")
def my_projects(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """The employee's own project assignments — id/name only, used to
    populate project pickers (e.g. logging time) without exposing the
    full assignment/role details of everyone else's assignments."""
    rows = (
        db.query(Project.id, Project.name, Project.status)
        .join(EmployeeProject, EmployeeProject.project_id == Project.id)
        .filter(EmployeeProject.employee_id == user.id)
        .all()
    )
    return [{"id": r.id, "name": r.name, "status": r.status} for r in rows]


@router.post("/{employee_id}/projects", status_code=status.HTTP_201_CREATED)
def assign_employee_to_project(
    employee_id: int,
    payload: ProjectAssignmentCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to assign projects")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if employee is None or project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee or project not found")

    assignment = EmployeeProject(
        employee_id=employee_id,
        project_id=payload.project_id,
        role_on_project=payload.role_on_project,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": assignment.id, "employee_id": employee_id, "project_id": payload.project_id}
