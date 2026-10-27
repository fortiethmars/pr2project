from datetime import datetime, timezone, timedelta
import pytest

from shared.domain import (
    BusinessRuleError, Department, Employee, ReportCriteria, WorkSession,
    build_employee_report, validate_department_head, validate_department_tree,
    validate_employee, validate_manager_tree, validate_unique_root_manager,
    worked_hours_in_period,
)

UTC = timezone.utc
PERIOD_START = datetime(2026, 9, 1, tzinfo=UTC)
PERIOD_END = datetime(2026, 10, 1, tzinfo=UTC)


def dept(id=1, parent_id=None, head_employee_id=1):
    return Department(id=id, name=f"Отдел {id}", parent_id=parent_id, head_employee_id=head_employee_id)


def employee(id, department_id=1, manager_id=None, rooms=frozenset({10, 20}), office=None, root=False):
    return Employee(id=id, full_name=f"Сотрудник {id}", department_id=department_id,
                    manager_id=manager_id, accessible_room_ids=frozenset(rooms),
                    office_room_id=office, is_root_manager=root)


def test_department_head_must_belong_to_same_department():
    employees = {1: employee(1, department_id=2, manager_id=None, root=True)}
    with pytest.raises(BusinessRuleError, match="принадлежать своему подразделению"):
        validate_department_head(dept(id=1, head_employee_id=1), employees)


def test_department_cycle_is_rejected():
    departments = {1: dept(1, 2), 2: dept(2, 1)}
    with pytest.raises(BusinessRuleError, match="цикл"):
        validate_department_tree(departments)


def test_missing_parent_department_is_rejected():
    with pytest.raises(BusinessRuleError, match="не существует"):
        validate_department_tree({1: dept(1, 999)})


def test_manager_cycle_is_rejected():
    employees = {1: employee(1, manager_id=2), 2: employee(2, manager_id=1)}
    with pytest.raises(BusinessRuleError, match="цикл"):
        validate_manager_tree(employees)


def test_employee_must_have_manager_except_root_manager():
    with pytest.raises(BusinessRuleError, match="указать руководителя"):
        validate_employee(employee(2, manager_id=None), {2: employee(2, manager_id=None)}, {1: dept()})


def test_root_manager_must_not_have_manager():
    root = employee(1, manager_id=2, root=True)
    with pytest.raises(BusinessRuleError, match="корневого руководителя"):
        validate_employee(root, {1: root, 2: employee(2, manager_id=1)}, {1: dept()})


def test_only_one_root_manager_allowed():
    with pytest.raises(BusinessRuleError, match="только один"):
        validate_unique_root_manager([employee(1, root=True), employee(2, root=True)])


def test_office_room_must_be_in_access_list():
    person = employee(2, manager_id=1, rooms={10}, office=20)
    with pytest.raises(BusinessRuleError, match="список доступных"):
        validate_employee(person, {1: employee(1, root=True), 2: person}, {1: dept()})


def test_empty_report_filters_are_rejected():
    criteria = ReportCriteria(frozenset(), frozenset({10, 20}), PERIOD_START, PERIOD_END)
    with pytest.raises(BusinessRuleError, match="подразделение"):
        criteria.validate()
    criteria = ReportCriteria(frozenset({1}), frozenset(), PERIOD_START, PERIOD_END)
    with pytest.raises(BusinessRuleError, match="помещение"):
        criteria.validate()


def test_invalid_report_period_is_rejected():
    criteria = ReportCriteria(frozenset({1}), frozenset({10, 20}), PERIOD_END, PERIOD_START)
    with pytest.raises(BusinessRuleError, match="позже начала"):
        criteria.validate()


def test_work_hours_use_overlap_with_selected_period_and_ignore_open_sessions():
    sessions = [
        WorkSession(1, PERIOD_START - timedelta(hours=2), PERIOD_START + timedelta(hours=3)),
        WorkSession(1, PERIOD_END - timedelta(hours=4), PERIOD_END + timedelta(hours=2)),
        WorkSession(1, PERIOD_START, None),
        WorkSession(2, PERIOD_START, PERIOD_START + timedelta(hours=99)),
    ]
    assert worked_hours_in_period(sessions, 1, PERIOD_START, PERIOD_END) == 7.0


def test_report_uses_direct_subordinates_selected_departments_and_selected_rooms_only():
    employees = {
        1: employee(1, department_id=1, manager_id=None, rooms={10, 20, 30}, root=True),
        2: employee(2, department_id=1, manager_id=1),
        3: employee(3, department_id=1, manager_id=1),
        4: employee(4, department_id=1, manager_id=1),
        5: employee(5, department_id=1, manager_id=2),
        6: employee(6, department_id=2, manager_id=1),
    }
    sessions = [WorkSession(1, PERIOD_START, PERIOD_START + timedelta(hours=12))]
    criteria = ReportCriteria(frozenset({1}), frozenset({10, 20}), PERIOD_START, PERIOD_END, min_hours=10)
    result = build_employee_report(employees, {1: dept(1), 2: dept(2)}, sessions, criteria)
    assert [row["employee_id"] for row in result] == [1]
    assert result[0]["direct_subordinates"] == 4
    assert result[0]["matching_rooms"] == 2
    assert result[0]["worked_hours"] == 12.0


def test_report_room_filter_requires_two_matching_rooms():
    employees = {
        1: employee(1, manager_id=None, rooms={10}, root=True),
        2: employee(2, manager_id=1), 3: employee(3, manager_id=1), 4: employee(4, manager_id=1),
    }
    criteria = ReportCriteria(frozenset({1}), frozenset({10, 20}), PERIOD_START, PERIOD_END)
    assert build_employee_report(employees, {1: dept()}, [], criteria) == []
