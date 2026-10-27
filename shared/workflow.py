"""Приклад прикладного слоя: проверка операций до записи в БД.

Персистентность и транзакции будут подключены через FastAPI-репозитории;
функции здесь намеренно не зависят от интерфейса конкретного клиента.
"""
from __future__ import annotations
from .domain import (
    BusinessRuleError, Department, Employee, validate_department_head,
    validate_department_tree, validate_employee, validate_manager_tree,
    validate_unique_root_manager,
)


def validate_enterprise_state(employees: dict[int, Employee], departments: dict[int, Department]) -> None:
    """Проверяет взаимосвязанные ограничения для полного состояния организации."""
    validate_unique_root_manager(employees.values())
    validate_department_tree(departments)
    validate_manager_tree(employees)
    for employee in employees.values():
        validate_employee(employee, employees, departments)
    for department in departments.values():
        validate_department_head(department, employees)


def require_existing_ids(ids: set[int] | frozenset[int], available_ids: set[int], label: str) -> None:
    missing = set(ids) - available_ids
    if missing:
        raise BusinessRuleError(f"Не найдены {label}: {', '.join(map(str, sorted(missing)))}.")
