"""Подключение к БД и SQLAlchemy-модели для API."""
from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()
from sqlalchemy import (Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, String, Text, DateTime, UniqueConstraint, create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://pr2_user:change_me@127.0.0.1:5432/pr2_enterprise")
_engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class DepartmentType(Base):
    __tablename__ = "department_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

class EmployeeType(Base):
    __tablename__ = "employee_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type_id: Mapped[int] = mapped_column(ForeignKey("department_types.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    head_employee_id: Mapped[int] = mapped_column(Integer, nullable=False)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(250), nullable=False)
    type_id: Mapped[int] = mapped_column(ForeignKey("employee_types.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", deferrable=True, initially="DEFERRED"), nullable=False)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", deferrable=True, initially="DEFERRED"))
    office_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    is_root_manager: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    __table_args__ = (CheckConstraint("manager_id IS NULL OR manager_id <> id", name="employees_not_self_manager"),)

class EmployeeRoomAccess(Base):
    __tablename__ = "employee_room_access"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), primary_key=True)

class WorkSession(Base):
    __tablename__ = "work_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="work_session_end_after_start"),)

Index("one_open_work_session_per_employee", WorkSession.employee_id, unique=True, postgresql_where=WorkSession.ended_at.is_(None), sqlite_where=WorkSession.ended_at.is_(None))

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
