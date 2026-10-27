"""HTTP API для настольного и веб-клиента. Интерфейсы не обращаются к БД напрямую."""
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import Department, DepartmentType, Employee, EmployeeRoomAccess, EmployeeType, Room, WorkSession, get_db
from .schemas import (
    ReferenceCreate,
    ReferenceOut,
    RoomOut,
    DepartmentOut,
    EmployeeOut,
    ReportRequest,
    WorkSessionStart,
    WorkSessionOut,
    EmployeeCreate,
    DepartmentWithHeadCreate,
)
from shared.domain import BusinessRuleError, Department as DomainDepartment, Employee as DomainEmployee, WorkSession as DomainWorkSession, ReportCriteria, build_employee_report
from shared.workflow import validate_enterprise_state
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI(title="Управление персоналом", version="0.3.0", description="Общий API для настольного и веб-клиента")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/", include_in_schema=False)
def frontend_home():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/{page_name}.html", include_in_schema=False)
def frontend_page(page_name: str):
    allowed_pages = {
        "index",
        "employees",
        "departments",
        "rooms",
        "work-time",
        "reports",
    }

    if page_name not in allowed_pages:
        raise HTTPException(status_code=404, detail="Страница не найдена.")

    return FileResponse(str(FRONTEND_DIR / f"{page_name}.html"))

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "personnel-api"}

@app.get("/api/reference/employee-types", response_model=list[ReferenceOut])
def list_employee_types(db: Session = Depends(get_db)):
    return list(db.scalars(select(EmployeeType).order_by(EmployeeType.name)).all())
@app.get("/api/reference/department-types", response_model=list[ReferenceOut])
def list_department_types(db: Session = Depends(get_db)):
    return list(db.scalars(select(DepartmentType).order_by(DepartmentType.name)).all())

@app.get("/api/reference/department-types", response_model=list[ReferenceOut])
def list_department_types(db: Session = Depends(get_db)):
    return list(db.scalars(select(DepartmentType).order_by(DepartmentType.name)).all())


@app.post(
    "/api/reference/department-types",
    response_model=ReferenceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_department_type(payload: ReferenceCreate, db: Session = Depends(get_db)):
    item = DepartmentType(name=payload.name, description=payload.description)
    db.add(item)

    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Тип подразделения с таким названием уже существует.",
        )

    return item

@app.post("/api/reference/employee-types", response_model=ReferenceOut, status_code=status.HTTP_201_CREATED)
def create_employee_type(payload: ReferenceCreate, db: Session = Depends(get_db)):
    item = EmployeeType(name=payload.name, description=payload.description)
    db.add(item)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Тип сотрудника с таким названием уже существует.")
    return item

@app.get("/api/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return list(db.scalars(select(Room).order_by(Room.name)).all())

@app.post("/api/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(payload: ReferenceCreate, db: Session = Depends(get_db)):
    item = Room(name=payload.name, description=payload.description)
    db.add(item)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Помещение с таким названием уже существует.")
    return item

@app.get("/api/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return list(db.scalars(select(Department).order_by(Department.name)).all())

@app.post("/api/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentWithHeadCreate, db: Session = Depends(get_db)):
    # Проверяем тип подразделения
    department_type = db.get(DepartmentType, payload.type_id)
    if department_type is None:
        raise HTTPException(status_code=404, detail="Тип подразделения не найден.")

    # Проверяем тип руководителя
    employee_type = db.get(EmployeeType, payload.head_type_id)
    if employee_type is None:
        raise HTTPException(status_code=404, detail="Тип сотрудника-руководителя не найден.")

    # Проверяем родительское подразделение, если оно задано
    if payload.parent_id is not None and db.get(Department, payload.parent_id) is None:
        raise HTTPException(status_code=404, detail="Родительское подразделение не найдено.")

    # Проверяем руководителя родительского подразделения
    if payload.head_manager_id is not None:
        manager = db.get(Employee, payload.head_manager_id)
        if manager is None:
            raise HTTPException(status_code=404, detail="Руководитель не найден.")

    # Проверяем помещения
    rooms = db.scalars(
        select(Room).where(Room.id.in_(payload.head_room_ids))
    ).all()
    if len(rooms) != len(set(payload.head_room_ids)):
        raise HTTPException(status_code=404, detail="Одно или несколько помещений не найдены.")

    try:
        department_id = db.execute(
            text("SELECT nextval(pg_get_serial_sequence('departments', 'id'))")
        ).scalar_one()

        employee_id = db.execute(
            text("SELECT nextval(pg_get_serial_sequence('employees', 'id'))")
        ).scalar_one()

        department = Department(
            id=department_id,
            name=payload.name,
            type_id=payload.type_id,
            parent_id=payload.parent_id,
            head_employee_id=employee_id,
        )
        db.add(department)
        db.flush()


        root_manager = db.scalar(
            select(Employee).where(Employee.is_root_manager.is_(True))
        )

        if payload.head_manager_id is not None:
            head_manager_id = payload.head_manager_id
        elif root_manager is not None:
            head_manager_id = root_manager.id
        else:
            raise HTTPException(
                status_code=409,
                detail="В базе нет корневого руководителя. Сначала создайте его.",
            )

        head = Employee(
            id=employee_id,
            full_name=payload.head_full_name,
            type_id=payload.head_type_id,
            department_id=department.id,
            manager_id=head_manager_id,
            office_room_id=payload.head_office_room_id,
            is_root_manager=False,
        )

        db.add(head)
        db.flush()

        for room_id in payload.head_room_ids:
            db.add(EmployeeRoomAccess(employee_id=head.id, room_id=room_id))

        db.commit()
        db.refresh(department)

    except IntegrityError as exc:
        db.rollback()
        print("ОШИБКА СОЗДАНИЯ ПОДРАЗДЕЛЕНИЯ:", repr(exc.orig))
        raise HTTPException(
            status_code=409,
            detail="Не удалось создать подразделение и руководителя. Проверь ограничения БД и данные.",
        )

    return department

@app.get("/api/employees", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return list(db.scalars(select(Employee).order_by(Employee.full_name)).all())

@app.post("/api/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    # Проверяем тип сотрудника
    employee_type = db.get(EmployeeType, payload.type_id)
    if employee_type is None:
        raise HTTPException(status_code=404, detail="Тип сотрудника не найден.")

    # Проверяем подразделение
    department = db.get(Department, payload.department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Подразделение не найдено.")

    # Проверяем руководителя
    if payload.manager_id is not None:
        manager = db.get(Employee, payload.manager_id)
        if manager is None:
            raise HTTPException(status_code=404, detail="Руководитель не найден.")

    # Проверяем помещения
    rooms = db.scalars(
        select(Room).where(Room.id.in_(payload.room_ids))
    ).all()
    if len(rooms) != len(set(payload.room_ids)):
        raise HTTPException(status_code=404, detail="Одно или несколько помещений не найдены.")

    employee = Employee(
        full_name=payload.full_name,
        type_id=payload.type_id,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        office_room_id=payload.office_room_id,
        is_root_manager=payload.is_root_manager,
    )

    try:
        db.add(employee)
        db.flush()

        for room_id in payload.room_ids:
            db.add(EmployeeRoomAccess(employee_id=employee.id, room_id=room_id))

        db.commit()
        db.refresh(employee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось создать сотрудника: нарушено ограничение базы данных.",
        )

    return employee


@app.get("/api/work-sessions", response_model=list[WorkSessionOut])
def list_work_sessions(db: Session = Depends(get_db)):
    return list(
        db.scalars(
            select(WorkSession).order_by(WorkSession.started_at.desc())
        ).all()
    )


@app.post(
    "/api/work-sessions/start",
    response_model=WorkSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def start_work_session(
    payload: WorkSessionStart,
    db: Session = Depends(get_db),
):
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден.")

    active_session = db.scalar(
        select(WorkSession).where(
            WorkSession.employee_id == payload.employee_id,
            WorkSession.ended_at.is_(None),
        )
    )
    if active_session is not None:
        raise HTTPException(
            status_code=409,
            detail="У сотрудника уже есть незакрытая рабочая запись.",
        )

    session = WorkSession(
        employee_id=payload.employee_id,
        started_at=datetime.now(timezone.utc),
        ended_at=None,
    )
    db.add(session)

    try:
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось начать рабочую запись. Возможно, она уже открыта.",
        )

    return session


@app.post("/api/work-sessions/{session_id}/finish",
          response_model=WorkSessionOut)
def finish_work_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    session = db.get(WorkSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Рабочая запись не найдена.")

    if session.ended_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Эта рабочая запись уже завершена.",
        )

    session.ended_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось завершить рабочую запись.",
        )

    return session

@app.post("/api/reports/employees")
def employee_report(payload: ReportRequest, db: Session = Depends(get_db)):
    """Формирует отчёт через общий доменный слой, используя данные из БД."""
    employees_db = list(db.scalars(select(Employee)).all())
    departments_db = list(db.scalars(select(Department)).all())
    access_db = list(db.scalars(select(EmployeeRoomAccess)).all())
    sessions_db = list(db.scalars(select(WorkSession)).all())
    access: dict[int, set[int]] = {}
    for item in access_db:
        access.setdefault(item.employee_id, set()).add(item.room_id)
    employees = {e.id: DomainEmployee(e.id, e.full_name, e.department_id, e.manager_id,
                frozenset(access.get(e.id, set())), e.office_room_id, e.is_root_manager) for e in employees_db}
    departments = {d.id: DomainDepartment(d.id, d.name, d.parent_id, d.head_employee_id) for d in departments_db}
    sessions = [DomainWorkSession(s.employee_id, s.started_at, s.ended_at) for s in sessions_db]
    
    criteria = ReportCriteria(
        frozenset(payload.department_ids),
        frozenset(payload.room_ids),
        payload.period_start,
        payload.period_end,
        payload.min_hours,
        payload.min_direct_subordinates,
        payload.min_matching_rooms,
    )

    try:
        validate_enterprise_state(employees, departments)

        result = build_employee_report(
            employees,
            departments,
            sessions,
            criteria,
        )

        department_names = {
            d.id: d.name
            for d in departments_db
        }

        for item in result:
            item["department_name"] = department_names.get(
                item["department_id"],
                "Неизвестное подразделение",
            )

        return result

    except BusinessRuleError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
