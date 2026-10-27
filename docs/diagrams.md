# Диаграммы проекта

## ER-диаграмма

```mermaid
erDiagram
    DEPARTMENT_TYPES ||--o{ DEPARTMENTS : classifies
    DEPARTMENTS o|--o{ DEPARTMENTS : parent
    EMPLOYEE_TYPES ||--o{ EMPLOYEES : classifies
    DEPARTMENTS ||--o{ EMPLOYEES : contains
    EMPLOYEES o|--o{ EMPLOYEES : manages
    EMPLOYEES ||--o{ DEPARTMENTS : heads
    ROOMS o|--o{ EMPLOYEES : office
    EMPLOYEES ||--o{ EMPLOYEE_ROOM_ACCESS : access
    ROOMS ||--o{ EMPLOYEE_ROOM_ACCESS : accessible
    EMPLOYEES ||--o{ WORK_SESSIONS : records
```

## Диаграмма классов — концептуальная

```mermaid
classDiagram
    class DepartmentType
    class Department
    class EmployeeType
    class Employee
    class Room
    class EmployeeRoomAccess
    class WorkSession
    class ReportService
    DepartmentType "1" --> "*" Department
    EmployeeType "1" --> "*" Employee
    Department "1" --> "*" Employee
    Department "0..1" --> "*" Department : parent
    Employee "0..1" --> "*" Employee : manager
    Employee "1" --> "*" WorkSession
    Employee "1" --> "*" EmployeeRoomAccess
    Room "1" --> "*" EmployeeRoomAccess
    Room "0..1" --> "*" Employee : office
    ReportService ..> Employee
    ReportService ..> Department
    ReportService ..> Room
    ReportService ..> WorkSession
```

## Use Case — перечень сценариев

Актор: «Пользователь системы».

- Вести сотрудников.
- Вести подразделения.
- Вести помещения.
- Вести типы сотрудников и подразделений.
- Назначать начальников и руководителей.
- Управлять доступом к помещениям.
- Начинать и завершать рабочие сессии.
- Формировать отчёт с обязательными фильтрами подразделений и помещений.
- Необязательно фильтровать результат по минимальным рабочим часам.

Для итоговой сдачи Use Case следует оформить как UML-диаграмму с границей системы, актором и овалами сценариев. Перечень здесь фиксирует содержание, а не претендует на графическую UML-нотацию.
