
const API = "/api";

const panels = document.querySelectorAll(".grid-2 > .panel");
const formPanel = panels[0];
const resultPanel = panels[1];

const departmentSelect = formPanel.querySelector("label:nth-child(1) select");
const roomSelect = formPanel.querySelector("label:nth-child(2) select");
const numberInputs = formPanel.querySelectorAll('input[type="number"]');
const checks = formPanel.querySelectorAll('input[type="checkbox"]');
const generateButton = formPanel.querySelector(".btn-primary");
const formNote = formPanel.querySelector(".empty-note");
const resultNote = resultPanel.querySelector(".empty-note");
const resultBody = resultPanel.querySelector("tbody");
const resultStats = resultPanel.querySelectorAll(".stat-value");
const downloadButton = resultPanel.querySelector(".btn-light");

let reportResults = "";

async function apiRequest(url, options = {}) {
  const response = await fetch(`${API}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail || "Ошибка запроса")
    );
  }

  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

async function loadOptions() {
  try {
    const [departments, rooms] = await Promise.all([
      apiRequest("/departments"),
      apiRequest("/rooms"),
    ]);

    departmentSelect.innerHTML =
      '<option value="">Все подразделения</option>' +
      departments.map((item) =>
        `<option value="${item.id}">${escapeHtml(item.name)}</option>`
      ).join("");

    roomSelect.multiple = true;
    roomSelect.size = Math.min(Math.max(rooms.length, 2), 5);
    roomSelect.innerHTML = rooms.map((item) =>
      `<option value="${item.id}">${escapeHtml(item.name)}</option>`
    ).join("");

    formNote.textContent =
      "Выбери подразделения и помещения. Для выбора нескольких помещений удерживай Ctrl.";
  } catch (error) {
    formNote.textContent = `Не удалось загрузить параметры: ${error.message}`;
  }
}

function renderResults(text) {
  reportResults = text;
  let rows;

  try {
    rows = JSON.parse(text);
  } catch {
    rows = null;
  }

  if (!Array.isArray(rows)) {
    resultBody.innerHTML = `
      <tr><td colspan="5">${escapeHtml(text)}</td></tr>
    `;
    resultNote.hidden = true;
    return;
  }

  resultBody.innerHTML = rows.map((item) => `
    <tr>
      <td>${escapeHtml(item.full_name ?? item.employee_name ?? "—")}</td>
      <td>${escapeHtml(item.department_name ?? "—")}</td>
      <td>${escapeHtml(item.direct_subordinates ?? item.subordinates ?? "—")}</td>
      <td>${escapeHtml(item.matching_rooms ?? item.room_count ?? "—")}</td>
      <td>${escapeHtml(item.worked_hours ?? item.hours ?? item.hours_per_month ?? "—")}</td>
    </tr>
  `).join("");

  resultNote.hidden = rows.length > 0;
  resultNote.textContent = rows.length
    ? ""
    : "По заданным условиям сотрудники не найдены.";

  resultStats[0].textContent = rows.length;

  const avgHours = rows.length
  ? rows.reduce((sum, item) =>
      sum + Number(item.worked_hours ?? item.hours ?? item.hours_per_month ?? 0), 0
    ) / rows.length
  : 0;

  const avgSubordinates = rows.length
    ? rows.reduce((sum, item) =>
        sum + Number(item.direct_subordinates ?? item.subordinates ?? 0), 0
      ) / rows.length
    : 0;

  resultStats[1].textContent = avgHours.toFixed(1);
  resultStats[2].textContent = avgSubordinates.toFixed(1);
}

generateButton.addEventListener("click", async () => {
  const selectedDepartments = departmentSelect.value
    ? [Number(departmentSelect.value)]
    : [];

  const selectedRooms = Array.from(roomSelect.selectedOptions)
    .map((option) => Number(option.value))
    .filter((id) => id > 0);

  if (!selectedDepartments.length) {
    formNote.textContent =
      "Выбери конкретное подразделение для отчёта.";
    return;
  }

  if (!selectedRooms.length) {
    formNote.textContent = "Выбери хотя бы одно помещение.";
    return;
  }

  const now = new Date();
  const end = new Date(now);
  const start = new Date(now);
  start.setMonth(start.getMonth() - 1);

  const lastMonth = checks[1]?.checked;
  if (lastMonth) {
    start.setDate(1);
    start.setMonth(start.getMonth() - 1);
    end.setDate(0);
  }

  const payload = {
    department_ids: selectedDepartments,
    room_ids: selectedRooms,
    period_start: start.toISOString(),
    period_end: end.toISOString(),
    min_hours: numberInputs[1].value === ""
      ? null
      : Number(numberInputs[1].value),
    min_direct_subordinates: numberInputs[0].value === ""
      ? 3
      : Number(numberInputs[0].value),
    min_matching_rooms: checks[0].checked ? 2 : 1,
  };

  generateButton.disabled = true;
  formNote.textContent = "Формируем отчёт…";

  try {
    const data = await apiRequest("/reports/employees", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    const text = typeof data === "string"
      ? data
      : JSON.stringify(data, null, 2);

    renderResults(text);
    formNote.textContent = "Отчёт сформирован.";
  } catch (error) {
    formNote.textContent = `Не удалось сформировать отчёт: ${error.message}`;
  } finally {
    generateButton.disabled = false;
  }
});

downloadButton.addEventListener("click", () => {
  if (!reportResults) {
    resultNote.textContent = "Сначала сформируй отчёт.";
    resultNote.hidden = false;
    return;
  }

  const blob = new Blob([reportResults], {
    type: "application/json;charset=utf-8",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "employee-report.json";
  link.click();
  URL.revokeObjectURL(url);
});

loadOptions();
