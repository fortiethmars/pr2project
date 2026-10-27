
const API = "/api";

const tableBody = document.querySelector(".table-wrap tbody");
const emptyNote = document.querySelector(".empty-note");
const addButton = document.querySelector(".toolbar .btn-primary");
const searchInput = document.querySelector(".field-search");
const dateInput = document.querySelector('input[type="date"]');
const statusSelect = document.querySelector(".toolbar select");

let employees = [];
let departments = [];
let sessions = [];

async function apiRequest(url, options = {}) {
  const response = await fetch(`${API}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Ошибка запроса к серверу");
  }

  return data;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function duration(start, end) {
  if (!end) return "В процессе";

  const minutes = Math.max(
    0,
    Math.floor((new Date(end) - new Date(start)) / 60000)
  );

  return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`;
}

function employeeById(id) {
  return employees.find(employee => employee.id === id);
}

function departmentName(id) {
  const department = departments.find(item => item.id === id);
  return department ? department.name : "—";
}

function renderTable() {
  const query = (searchInput.value || "").trim().toLowerCase();
  const selectedDate = dateInput.value;
  const selectedStatus = statusSelect.value;

  const filtered = sessions.filter(session => {
    const employee = employeeById(session.employee_id);
    const name = employee?.full_name || `Сотрудник #${session.employee_id}`;

    if (query && !name.toLowerCase().includes(query)) return false;

    if (selectedDate) {
      const sessionDate = new Date(session.started_at);
      const localDate = [
        sessionDate.getFullYear(),
        String(sessionDate.getMonth() + 1).padStart(2, "0"),
        String(sessionDate.getDate()).padStart(2, "0")
      ].join("-");

      if (localDate !== selectedDate) return false;
    }

    const status = session.ended_at ? "closed" : "open";

    if (selectedStatus && selectedStatus !== status) return false;

    return true;
  });

  tableBody.innerHTML = "";

  for (const session of filtered) {
    const employee = employeeById(session.employee_id);
    const status = session.ended_at ? "Завершена" : "В процессе";
    const row = document.createElement("tr");

    const values = [
      employee?.full_name || `Сотрудник #${session.employee_id}`,
      employee ? departmentName(employee.department_id) : "—",
      formatDate(session.started_at),
      formatDate(session.ended_at),
      duration(session.started_at, session.ended_at),
      status
    ];

    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    }

    const actionCell = document.createElement("td");

    if (!session.ended_at) {
      const finishButton = document.createElement("button");
      finishButton.className = "btn btn-light";
      finishButton.textContent = "Завершить";

      finishButton.addEventListener("click", async () => {
        finishButton.disabled = true;

        try {
          await apiRequest(
            `/work-sessions/${session.id}/finish`,
            { method: "POST" }
          );
          await loadSessions();
        } catch (error) {
          alert(error.message);
          finishButton.disabled = false;
        }
      });

      actionCell.appendChild(finishButton);
    }

    row.appendChild(actionCell);
    tableBody.appendChild(row);
  }

  emptyNote.hidden = filtered.length > 0;
  emptyNote.textContent = filtered.length
    ? ""
    : "Записей рабочего времени пока нет.";

  updateStats();
}

function updateStats() {
  const today = new Date().toLocaleDateString("sv-SE");

  const todaySessions = sessions.filter(session => {
    return new Date(session.started_at).toLocaleDateString("sv-SE") === today;
  });

  const activeCount = sessions.filter(session => !session.ended_at).length;
  const completedToday = todaySessions.filter(session => session.ended_at);
  const totalMinutes = completedToday.reduce((sum, session) => {
    return sum + Math.max(
      0,
      (new Date(session.ended_at) - new Date(session.started_at)) / 60000
    );
  }, 0);

  const averageMinutes = completedToday.length
    ? Math.round(totalMinutes / completedToday.length)
    : 0;

  const metricValues = document.querySelectorAll(".time-metrics .metric-value");
  if (metricValues[0]) metricValues[0].textContent = todaySessions.length;
  if (metricValues[1]) {
    metricValues[1].textContent =
      `${Math.floor(averageMinutes / 60)} ч ${averageMinutes % 60} мин`;
  }
  if (metricValues[2]) {
    metricValues[2].textContent =
      todaySessions.filter(session => !session.ended_at).length;
  }

  const statValues = document.querySelectorAll(".stats .stat-value");
  if (statValues[0]) statValues[0].textContent = activeCount;
  if (statValues[1]) statValues[1].textContent = completedToday.length;
  if (statValues[2]) {
    const employeesWithSessions = new Set(
      todaySessions.map(session => session.employee_id)
    );
    statValues[2].textContent = employees.filter(
      employee => !employeesWithSessions.has(employee.id)
    ).length;
  }
  if (statValues[3]) {
    statValues[3].textContent =
      `${Math.floor(averageMinutes / 60)} ч ${averageMinutes % 60} мин`;
  }
}

async function loadSessions() {
  sessions = await apiRequest("/work-sessions");
  renderTable();
}

async function loadPageData() {
  try {
    const [employeeData, departmentData] = await Promise.all([
      apiRequest("/employees"),
      apiRequest("/departments")
    ]);

    employees = employeeData;
    departments = departmentData;

    await loadSessions();
  } catch (error) {
    emptyNote.hidden = false;
    emptyNote.textContent = `Не удалось загрузить данные: ${error.message}`;
  }
}

function addWorkSession() {
  if (!employees.length) {
    alert("Сначала добавь сотрудника в разделе «Сотрудники».");
    return;
  }

  const options = employees
    .map(employee => `${employee.id}: ${employee.full_name}`)
    .join("\n");

  const answer = prompt(
    `Введи ID сотрудника, которому нужно отметить начало работы:\n\n${options}`
  );

  if (answer === null) return;

  const employeeId = Number(answer);

  if (!Number.isInteger(employeeId) ||
      !employees.some(employee => employee.id === employeeId)) {
    alert("Укажи корректный ID сотрудника из списка.");
    return;
  }

  apiRequest("/work-sessions/start", {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId })
  })
    .then(loadSessions)
    .catch(error => alert(error.message));
}

addButton.addEventListener("click", addWorkSession);
searchInput.addEventListener("input", renderTable);
dateInput.addEventListener("change", renderTable);

statusSelect.innerHTML = `
  <option value="">Все статусы</option>
  <option value="open">В процессе</option>
  <option value="closed">Завершена</option>
`;

statusSelect.addEventListener("change", renderTable);

loadPageData();
