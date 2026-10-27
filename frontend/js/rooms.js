
const API = "/api";

const stats = document.querySelectorAll(".stats .stat-value");
const addButton = document.querySelector(".page-heading .btn-primary");
const searchInput = document.querySelector(".field-search");
const emptyNote = document.querySelector(".empty-note");
const panel = document.querySelector(".panel");

let rooms = [];

async function apiRequest(url, options = {}) {
  const response = await fetch(`${API}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Ошибка запроса к серверу");
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

function renderRooms() {
  const query = searchInput.value.trim().toLowerCase();

  const filtered = rooms.filter((room) =>
    `${room.name} ${room.description || ""}`.toLowerCase().includes(query)
  );

  let list = panel.querySelector(".rooms-list");

  if (!list) {
    list = document.createElement("div");
    list.className = "rooms-list";
    emptyNote.before(list);
  }

  list.innerHTML = filtered.map((room) => `
    <article class="panel" style="margin-bottom:12px">
      <div class="panel-heading">
        <div>
          <h2>${escapeHtml(room.name)}</h2>
          <p>${escapeHtml(room.description || "Описание не указано")}</p>
        </div>
      </div>
    </article>
  `).join("");

  emptyNote.hidden = filtered.length > 0;
  emptyNote.textContent = query && rooms.length
    ? "По запросу ничего не найдено."
    : "Помещения пока не добавлены.";

  stats[0].textContent = rooms.length;
  stats[1].textContent = "—";
  stats[2].textContent = "—";
  stats[3].textContent = "—";
}

async function loadRooms() {
  try {
    rooms = await apiRequest("/rooms");
    renderRooms();
  } catch (error) {
    emptyNote.hidden = false;
    emptyNote.textContent = `Не удалось загрузить помещения: ${error.message}`;
  }
}

function showRoomForm() {
  if (document.querySelector("#roomDialog")) return;

  const dialog = document.createElement("dialog");
  dialog.id = "roomDialog";
  dialog.innerHTML = `
    <form id="roomForm" style="padding:24px;min-width:320px">
      <h2>Новое помещение</h2>
      <label for="roomName">Название помещения</label>
      <input class="field" id="roomName" name="name"
             maxlength="200" required style="width:100%;margin:12px 0">
      <label for="roomDescription">Описание</label>
      <textarea class="field" id="roomDescription" name="description"
                rows="3" style="width:100%;margin:12px 0"></textarea>
      <p id="roomError" style="color:#ff6262"></p>
      <div style="display:flex;justify-content:flex-end;gap:8px">
        <button type="button" class="btn btn-light" id="roomCancel">Отмена</button>
        <button type="submit" class="btn btn-primary">Создать</button>
      </div>
    </form>
  `;

  document.body.append(dialog);
  dialog.showModal();

  dialog.querySelector("#roomCancel").addEventListener("click", () => {
    dialog.close();
    dialog.remove();
  });

  dialog.querySelector("#roomForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const name = dialog.querySelector("#roomName").value.trim();
    const description = dialog.querySelector("#roomDescription").value.trim();
    const errorElement = dialog.querySelector("#roomError");
    const submitButton = dialog.querySelector('[type="submit"]');

    if (!name) {
      errorElement.textContent = "Укажи название помещения.";
      return;
    }

    submitButton.disabled = true;
    errorElement.textContent = "";

    try {
      await apiRequest("/rooms", {
        method: "POST",
        body: JSON.stringify({ name, description }),
      });

      dialog.close();
      dialog.remove();
      await loadRooms();
    } catch (error) {
      errorElement.textContent = error.message;
      submitButton.disabled = false;
    }
  });
}

addButton.addEventListener("click", showRoomForm);
searchInput.addEventListener("input", renderRooms);

loadRooms();
