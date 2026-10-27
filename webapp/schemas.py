"""Pydantic-схемы входных и выходных данных API."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ReferenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None

    @model_validator(mode="after")
    def trim_name(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Название не может быть пустым.")
        return self

class ReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None

class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None

class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type_id: int
    parent_id: int | None
    head_employee_id: int

class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    type_id: int
    department_id: int
    manager_id: int | None
    office_room_id: int | None
    is_root_manager: bool
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type_id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    head_employee_id: int = Field(gt=0)

class DepartmentWithHeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type_id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)

    head_full_name: str = Field(min_length=1, max_length=250)
    head_type_id: int = Field(gt=0)
    head_manager_id: int | None = Field(default=None, gt=0)
    head_office_room_id: int | None = Field(default=None, gt=0)
    head_room_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_names_and_rooms(self):
        self.name = self.name.strip()
        self.head_full_name = self.head_full_name.strip()

        if not self.name:
            raise ValueError("Название подразделения не может быть пустым.")
        if not self.head_full_name:
            raise ValueError("ФИО руководителя не может быть пустым.")
        if any(room_id <= 0 for room_id in self.head_room_ids):
            raise ValueError("Идентификаторы помещений должны быть положительными.")
        if len(self.head_room_ids) != len(set(self.head_room_ids)):
            raise ValueError("Список помещений не должен содержать дубликаты.")
        if (
            self.head_office_room_id is not None
            and self.head_office_room_id not in self.head_room_ids
        ):
            raise ValueError(
                "Кабинет руководителя должен входить в список доступных помещений."
            )

        return self

class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=250)
    type_id: int = Field(gt=0)
    department_id: int = Field(gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    office_room_id: int | None = Field(default=None, gt=0)
    is_root_manager: bool = False
    room_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_employee(self):
        self.full_name = self.full_name.strip()

        if not self.full_name:
            raise ValueError("ФИО сотрудника не может быть пустым.")

        if any(room_id <= 0 for room_id in self.room_ids):
            raise ValueError("Идентификаторы помещений должны быть положительными.")

        if len(self.room_ids) != len(set(self.room_ids)):
            raise ValueError("Список помещений не должен содержать дубликаты.")

        if self.office_room_id is not None and self.office_room_id not in self.room_ids:
            raise ValueError("Кабинет сотрудника должен входить в список доступных помещений.")

        if self.is_root_manager and self.manager_id is not None:
            raise ValueError("У руководителя организации не должно быть руководителя.")

        if not self.is_root_manager and self.manager_id is None:
            raise ValueError("У сотрудника должен быть указан руководитель.")

        return self
class ReportRequest(BaseModel):
    department_ids: list[int] = Field(min_length=1)
    room_ids: list[int] = Field(min_length=1)
    period_start: datetime
    period_end: datetime
    min_hours: float | None = Field(default=None, ge=0)
    min_direct_subordinates: int = Field(default=3, ge=0)
    min_matching_rooms: int = Field(default=2, ge=1)

    @model_validator(mode="after")
    def valid_period(self):
        if self.period_end <= self.period_start:
            raise ValueError("Конец периода должен быть позже начала.")
        return self


class WorkSessionStart(BaseModel):
    employee_id: int = Field(gt=0)


class WorkSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    started_at: datetime
    ended_at: datetime | None = None