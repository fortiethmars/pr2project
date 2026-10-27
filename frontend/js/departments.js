
const API = "/api";

const stats = document.querySelectorAll(".stats .stat-value");
const addButton = document.querySelector(".page-heading .btn-primary");
const searchInput = document.querySelector(".field-search");
const typeSelect = document.querySelector(".toolbar select");
const emptyNote = document.querySelector(".empty-note");
const panelHeading = document.querySelector(".panel-heading");

let departments = [];
let departmentTypes = [];
let employees = [];
let employeeTypes = [];
let rooms = [];

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

function makeSelectOptions(items, placeholder, labelField = "name") {
  return `<option value="">${placeholder}</option>` + items.map(item =>
    `<option value="${item.id}">${escapeHtml(item[labelField])}</option>`
  ).join("");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function renderDepartments() {
  const query = searchInput.value.trim().toLowerCase();
  const selectedType = typeSelect.value;

  const filtered = departments.filter(department => {
    const type = departmentTypes.find(item => item.id === department.type_id);
    const nameMatches = department.name.toLowerCase().includes(query);
    const typeMatches = !selectedType || String(department.type_id) === selectedType;
    return nameMatches && typeMatches;
  });

  stats[0].textContent = departments.length;
  stats[1].textContent = departments.filter(item => item.parent_id == null).length;
  stats[2].textContent = departments.filter(item => !item.head_employee_id).length;
  stats[3].textContent = employees.length;

  typeSelect.innerHTML = makeSelectOptions(
    departmentTypes,
    "Все типы подразделений"
  );
  typeSelect.value = selectedType;

  panelHeading.innerHTML = `
    <div>
      <h2>Дерево подразделений</h2>
      <p>Подразделения и их руководители из базы данных.</p>
    </div>
  `;

  if (!filtered.length) {
    emptyNote.hidden = false;
    emptyNote.textContent = query || selectedType
      ? "Подразделения по выбранным условиям не найдены."
      : "Подразделений пока нет.";
    return;
  }

  emptyNote.hidden = true;

  const existingTree = document.querySelector(".department-tree");
  if (existingTree) existingTree.remove();

  const tree = document.createElement("div");
  tree.className = "department-tree";

  const visibleIds = new Set(filtered.map(item => item.id));

  function addDepartment(department, container, level = 0) {
    const head = employees.find(employee =>
      employee.id === department.head_employee_id
    );

    const type = departmentTypes.find(item => item.id === department.type_id);

    const card = document.createElement("div");
    card.style.cssText = `
      margin: 10px 0 10px ${level * 24}px;
      padding: 16px;
      border: 1px solid var(--border-color, #333);
      border-radius: 12px;
    `;

    const title = document.createElement("strong");
    title.textContent = department.name;

    const details = document.createElement("p");
    details.style.margin = "8px 0 0";
    details.textContent =
      `${type?.name || "Тип не указан"} · Руководитель: ${head?.full_name || "не найден"}`;

    card.append(title, details);
    container.appendChild(card);

    filtered
      .filter(child => child.parent_id === department.id && visibleIds.has(child.id))
      .forEach(child => addDepartment(child, container, level + 1));
  }

  const roots = filtered.filter(item =>
    item.parent_id == null || !visibleIds.has(item.parent_id)
  );

  roots.forEach(root => addDepartment(root, tree));
  emptyNote.parentNode.insertBefore(tree, emptyNote);
}

function showDepartmentForm() {
  const existing = document.getElementById("departmentDialog");
  if (existing) existing.remove();

  const dialog = document.createElement("dialog");
  dialog.id = "departmentDialog";
  dialog.style.cssText = "width:min(640px, 94vw); max-height:90vh; overflow:auto; border-radius:16px;";

  dialog.innerHTML = `
    <form id="departmentForm">
      <h2>Новое подразделение</h2>

      <label>Название подразделения
        <input class="field" name="name" required maxlength="200">
      </label>

      <label>Тип подразделения
        <select class="select" name="type_id" required>
          ${makeSelectOptions(departmentTypes, "Выбери тип")}
        </select>
      </label>

      <label>Родительское подразделение
        <select class="select" name="parent_id">
          <option value="">Верхний уровень</option>
          ${departments.map(item =>
            `<option value="${item.id}">${escapeHtml(item.name)}</option>`
          ).join("")}
        </select>
      </label>

      <hr>
      <h3>Первый руководитель</h3>

      <label>ФИО руководителя
        <input class="field" name="head_full_name" required maxlength="250">
      </label>

      <label>Тип сотрудника
        <select class="select" name="head_type_id" required>
          ${makeSelectOptions(employeeTypes, "Выбери тип сотрудника")}
        </select>
      </label>

      <label>Кабинет руководителя
        <select class="select" name="head_office_room_id">
          <option value="">Не назначен</option>
          ${rooms.map(room =>
            `<option value="${room.id}">${escapeHtml(room.name)}</option>`
          ).join("")}
        </select>
      </label>

      <label>Доступные помещения
        <select class="select" name="head_room_ids" multiple size="4">
          ${rooms.map(room =>
            `<option value="${room.id}">${escapeHtml(room.name)}</option>`
          ).join("")}
        </select>
      </label>

      <p class="form-error" style="color:#ff7070"></p>

      <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:18px">
        <button type="button" class="btn btn-light" id="cancelDepartment">Отмена</button>
        <button type="submit" class="btn btn-primary">Создать</button>
      </div>
    </form>
  `;

  document.body.appendChild(dialog);
  dialog.showModal();

  const form = dialog.querySelector("#departmentForm");
  const officeSelect = form.elements.head_office_room_id;
  const roomSelect = form.elements.head_room_ids;

  officeSelect.addEventListener("change", () => {
    const officeId = officeSelect.value;
    if (officeId) {
      Array.from(roomSelect.options).forEach(option => {
        if (option.value === officeId) option.selected = true;
      });
    }
  });

  dialog.querySelector("#cancelDepartment").addEventListener("click", () => {
    dialog.close();
    dialog.remove();
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();

    const errorBox = form.querySelector(".form-error");
    errorBox.textContent = "";

    const data = new FormData(form);
    const selectedRooms = Array.from(roomSelect.selectedOptions)
      .map(option => Number(option.value));

    const officeRoom = officeSelect.value
      ? Number(officeSelect.value)
      : null;

    if (officeRoom !== null && !selectedRooms.includes(officeRoom)) {
      errorBox.textContent = "Кабинет руководителя должен входить в доступные помещения.";
      return;
    }

    const payload = {
      name: data.get("name").trim(),
      type_id: Number(data.get("type_id")),
      parent_id: data.get("parent_id")
        ? Number(data.get("parent_id"))
        : null,
      head_full_name: data.get("head_full_name").trim(),
      head_type_id: Number(data.get("head_type_id")),
      head_manager_id: null,
      head_office_room_id: officeRoom,
      head_room_ids: selectedRooms
    };

    const submitButton = form.querySelector('[type="submit"]');
    submitButton.disabled = true;

    try {
      await apiRequest("/departments", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      dialog.close();
      dialog.remove();
      await loadPageData();
    } catch (error) {
      errorBox.textContent = error.message;
      submitButton.disabled = false;
    }
  });
}

async function loadPageData() {
  emptyNote.hidden = false;
  emptyNote.textContent = "Загрузка подразделений...";

  try {
    const results = await Promise.all([
      apiRequest("/departments"),
      apiRequest("/reference/department-types"),
      apiRequest("/employees"),
      apiRequest("/reference/employee-types"),
      apiRequest("/rooms")
    ]);

    [departments, departmentTypes, employees, employeeTypes, rooms] = results;

    renderDepartments();
  } catch (error) {
    emptyNote.hidden = false;
    emptyNote.textContent = `Не удалось загрузить данные: ${error.message}`;
  }
}

addButton.addEventListener("click", showDepartmentForm);
searchInput.addEventListener("input", renderDepartments);

typeSelect.addEventListener("change", renderDepartments);

loadPageData();
