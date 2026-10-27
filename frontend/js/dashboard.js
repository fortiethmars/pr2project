
async function loadDashboard() {
    const stats = document.querySelectorAll(".stat-card .stat-value");
    const statusBadge = document.querySelector(".badge");
    const emptyNotes = document.querySelectorAll(".empty-note");

    try {
        const [employees, departments, rooms, sessions] = await Promise.all([
            fetch("/api/employees").then(response => {
                if (!response.ok) throw new Error("Ошибка загрузки сотрудников");
                return response.json();
            }),
            fetch("/api/departments").then(response => {
                if (!response.ok) throw new Error("Ошибка загрузки подразделений");
                return response.json();
            }),
            fetch("/api/rooms").then(response => {
                if (!response.ok) throw new Error("Ошибка загрузки помещений");
                return response.json();
            }),
            fetch("/api/work-sessions").then(response => {
                if (!response.ok) throw new Error("Ошибка загрузки рабочего времени");
                return response.json();
            })
        ]);

        // Статистика
        stats[0].textContent = employees.length;
        stats[1].textContent = departments.length;
        stats[2].textContent = rooms.length;

        const today = new Date().toDateString();

        const employeesAtWorkToday = new Set(
            sessions
                .filter(session =>
                    session.started_at &&
                    new Date(session.started_at).toDateString() === today &&
                    !session.ended_at
                )
                .map(session => session.employee_id)
        );

        stats[3].textContent = employeesAtWorkToday.size;
        
        // Количество незавершённых рабочих сессий
        const openSessionsCount = sessions.filter(
            session => !session.ended_at
        ).length;

        const openSessionsElement = document.getElementById("open-sessions-count");
        if (openSessionsElement) {
            openSessionsElement.textContent = openSessionsCount;
        }

        // Время последнего обновления главной страницы
        const updatedAtElement = document.getElementById("dashboard-updated-at");
        if (updatedAtElement) {
            updatedAtElement.textContent = new Date().toLocaleTimeString("ru-RU", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            });
        }

        // Названия подразделений
        const departmentNames = new Map(
            departments.map(department => [
                department.id,
                department.name
            ])
        );

        // Последние сотрудники
        const employeeTable = document.querySelector(
            ".grid-2 .panel:first-child tbody"
        );

        if (employeeTable) {
            employeeTable.replaceChildren();

            [...employees]
                .sort((a, b) => b.id - a.id)
                .slice(0, 5)
                .forEach(employee => {
                    const row = document.createElement("tr");

                    const isWorking = sessions.some(session =>
                        session.employee_id === employee.id &&
                        !session.ended_at
                    );

                    const values = [
                        employee.full_name,
                        departmentNames.get(employee.department_id) || "Не указано",
                        isWorking ? "На работе" : "Не на работе"
                    ];

                    values.forEach(value => {
                        const cell = document.createElement("td");
                        cell.textContent = value;
                        row.appendChild(cell);
                    });

                    employeeTable.appendChild(row);
                });
        }

        // Структура предприятия
        const departmentPanel = document.querySelector(
            ".grid-2 .panel:nth-child(2)"
        );

        if (departmentPanel) {
            let departmentList = departmentPanel.querySelector(
                ".dashboard-departments"
            );

            if (!departmentList) {
                departmentList = document.createElement("div");
                departmentList.className = "dashboard-departments";
                departmentPanel.appendChild(departmentList);
            }

            departmentList.replaceChildren();

            departments.forEach(department => {
                const employeeCount = employees.filter(
                    employee => employee.department_id === department.id
                ).length;

                const item = document.createElement("p");
                item.textContent =
                    `${department.name} — сотрудников: ${employeeCount}`;

                departmentList.appendChild(item);
            });
        }

        // Убираем заглушки
        emptyNotes.forEach(note => {
            note.hidden = true;
        });

        // Статус подключения
        if (statusBadge) {
            statusBadge.textContent = "Сервер подключён";
            statusBadge.classList.remove("badge-blue");
        }

    } catch (error) {
        console.error("Ошибка загрузки главной страницы:", error);

        if (statusBadge) {
            statusBadge.textContent = "Ошибка подключения";
        }
    }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
