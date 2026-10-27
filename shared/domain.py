"""Доменные модели и типы для общей бизнес-логики."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable


class BusinessRuleError(ValueError):
    """Операция нарушает бизнес-правило предметной области."""


@dataclass(frozen=True)
class Department:
    id: int
    name: str
    parent_id: int | None
    head_employee_id: int


@dataclass(frozen=True)
class Employee:
    id: int
    full_name: str
    department_id: int
    manager_id: int | None
    accessible_room_ids: frozenset[int] = field(default_factory=frozenset)
    office_room_id: int | None = None
    is_root_manager: bool = False


@dataclass(frozen=True)
class WorkSession:
    employee_id: int
    started_at: datetime
    ended_at: datetime | None = None


@dataclass(frozen=True)
class ReportCriteria:
    department_ids: frozenset[int]
    room_ids: frozenset[int]
    period_start: datetime
    period_end: datetime
    min_hours: float | None = None
    min_direct_subordinates: int = 3
    min_matching_rooms: int = 2

    def validate(self) -> None:
        if not self.department_ids:
            raise BusinessRuleError("Выберите хотя бы одно подразделение.")
        if not self.room_ids:
            raise BusinessRuleError("Выберите хотя бы одно помещение.")
        if self.period_end <= self.period_start:
            raise BusinessRuleError("Конец периода должен быть позже начала.")
        if self.min_hours is not None and self.min_hours < 0:
            raise BusinessRuleError("Минимальное количество часов не может быть отрицательным.")
        if self.min_direct_subordinates < 0 or self.min_matching_rooms < 1:
            raise BusinessRuleError("Некорректные пороговые значения отчёта.")


def validate_employee(employee: Employee, employees: dict[int, Employee], departments: dict[int, Department]) -> None:
    """Проверяет локальные правила сотрудника; глобальные циклы проверяются отдельно."""
    if not employee.full_name.strip():
        raise BusinessRuleError("ФИО сотрудника не может быть пустым.")
    if employee.department_id not in departments:
        raise BusinessRuleError("Указанное подразделение не существует.")
    if employee.is_root_manager:
        if employee.manager_id is not None:
            raise BusinessRuleError("У корневого руководителя не должно быть руководителя.")
    else:
        if employee.manager_id is None:
            raise BusinessRuleError("Для сотрудника необходимо указать руководителя.")
        if employee.manager_id == employee.id:
            raise BusinessRuleError("Сотрудник не может быть собственным руководителем.")
        if employee.manager_id not in employees:
            raise BusinessRuleError("Указанный руководитель не существует.")
    if employee.office_room_id is not None and employee.office_room_id not in employee.accessible_room_ids:
        raise BusinessRuleError("Рабочий кабинет должен входить в список доступных помещений.")


def validate_unique_root_manager(employees: Iterable[Employee]) -> None:
    if sum(1 for employee in employees if employee.is_root_manager) > 1:
        raise BusinessRuleError("В организации может быть только один корневой руководитель.")


def validate_department_head(department: Department, employees: dict[int, Employee]) -> None:
    head = employees.get(department.head_employee_id)
    if head is None:
        raise BusinessRuleError("Руководитель подразделения не существует.")
    if head.department_id != department.id:
        raise BusinessRuleError("Руководитель должен принадлежать своему подразделению.")


def validate_department_tree(departments: dict[int, Department]) -> None:
    """Отклоняет циклы в дереве подразделений, включая ссылки на отсутствительные узлы."""
    for department in departments.values():
        if department.parent_id is not None and department.parent_id not in departments:
            raise BusinessRuleError(f"Родительское подразделение {department.parent_id} не существует.")
        visited: set[int] = set()
        current: Department | None = department
        while current is not None:
            if current.id in visited:
                raise BusinessRuleError("В иерархии подразделений обнаружен цикл.")
            visited.add(current.id)
            current = departments.get(current.parent_id) if current.parent_id is not None else None


def validate_manager_tree(employees: dict[int, Employee]) -> None:
    """Отклоняет циклы в отношениях руководитель—подчинённый."""
    for employee in employees.values():
        visited: set[int] = set()
        current: Employee | None = employee
        while current is not None:
            if current.id in visited:
                raise BusinessRuleError("В иерархии подчинения обнаружен цикл.")
            visited.add(current.id)
            if current.manager_id is None:
                break
            current = employees.get(current.manager_id)
            if current is None:
                raise BusinessRuleError("В иерархии указан несуществующий руководитель.")


def worked_hours_in_period(sessions: Iterable[WorkSession], employee_id: int,
                           period_start: datetime, period_end: datetime) -> float:
    """Суммирует пересечение закрытых сессий сотрудника с выбранным периодом.

    Открытые сессии не включаются в отчёт, так как их фактическая длительность
    ещё не известна. Все даты должны быть согласованы по timezone-awareness.
    """
    seconds = 0.0
    for session in sessions:
        if session.employee_id != employee_id or session.ended_at is None:
            continue
        start = max(session.started_at, period_start)
        end = min(session.ended_at, period_end)
        if end > start:
            seconds += (end - start).total_seconds()
    return seconds / 3600.0


def build_employee_report(employees: dict[int, Employee], departments: dict[int, Department],
                          sessions: Iterable[WorkSession], criteria: ReportCriteria) -> list[dict[str, object]]:
    """Возвращает сотрудников, удовлетворяющих всем условиям отчёта.

    Учитываются только прямые подчинённые и только явно выбранные подразделения.
    Условие по рабочим часам применяется, только если min_hours задан.
    """
    criteria.validate()
    subordinate_counts: dict[int, int] = {}
    for employee in employees.values():
        if employee.manager_id is not None:
            subordinate_counts[employee.manager_id] = subordinate_counts.get(employee.manager_id, 0) + 1

    result: list[dict[str, object]] = []
    sessions = tuple(sessions)
    for employee in employees.values():
        if employee.department_id not in criteria.department_ids:
            continue
        if subordinate_counts.get(employee.id, 0) < criteria.min_direct_subordinates:
            continue
        if len(employee.accessible_room_ids.intersection(criteria.room_ids)) < criteria.min_matching_rooms:
            continue
        hours = worked_hours_in_period(sessions, employee.id, criteria.period_start, criteria.period_end)
        if criteria.min_hours is not None and hours < criteria.min_hours:
            continue
        result.append({
            "employee_id": employee.id,
            "full_name": employee.full_name,
            "department_id": employee.department_id,
            "direct_subordinates": subordinate_counts.get(employee.id, 0),
            "matching_rooms": len(employee.accessible_room_ids.intersection(criteria.room_ids)),
            "worked_hours": round(hours, 2),
        })
    return sorted(result, key=lambda row: str(row["full_name"]).casefold())
