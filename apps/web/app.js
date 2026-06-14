/*
 * Hora Marcada - frontend.
 * Consome a API atraves do API Gateway no caminho relativo "/api"
 * (o nginx faz proxy de /api -> api-gateway; no Kubernetes o Ingress roteia).
 *
 * Seguranca (RNF09): todo dado vindo da API e inserido via textContent /
 * createElement, nunca via innerHTML, evitando XSS.
 */
const API = "/api";

const store = {
  get token() {
    return localStorage.getItem("hm_token");
  },
  get role() {
    return localStorage.getItem("hm_role");
  },
  get name() {
    return localStorage.getItem("hm_name");
  },
  set(token, role, name) {
    localStorage.setItem("hm_token", token);
    localStorage.setItem("hm_role", role);
    localStorage.setItem("hm_name", name);
  },
  clear() {
    localStorage.removeItem("hm_token");
    localStorage.removeItem("hm_role");
    localStorage.removeItem("hm_name");
  },
  get isLogged() {
    return Boolean(this.token);
  },
};

const $ = (sel) => document.querySelector(sel);

let toastTimer = null;
function toast(message, type = "info") {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.hidden = true;
  }, 3500);
}

async function api(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && store.token) headers.Authorization = `Bearer ${store.token}`;

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    if (res.status === 401) {
      store.clear();
      renderAuth();
    }
    const detail = data && data.detail ? data.detail : `Erro ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : "Erro na requisicao");
  }
  return data;
}

/* ----------------------------------------------------------------------- */
/* Estado de autenticacao                                                  */
/* ----------------------------------------------------------------------- */
function renderAuth() {
  const area = $("#authArea");
  area.replaceChildren();

  if (store.isLogged) {
    const hello = document.createElement("span");
    hello.className = "auth-user";
    hello.textContent = `Ola, ${store.name}`;

    const out = document.createElement("button");
    out.className = "button ghost";
    out.type = "button";
    out.textContent = "Sair";
    out.addEventListener("click", () => {
      store.clear();
      renderAuth();
      toast("Sessao encerrada.");
    });

    area.append(hello, out);
  } else {
    const link = document.createElement("a");
    link.className = "login-link";
    link.href = "#login";
    link.textContent = "Entrar";
    area.append(link);
  }

  // Mostra/esconde elementos exclusivos de admin (RNF10).
  const isAdmin = store.role === "admin";
  document.querySelectorAll('[data-role="admin"]').forEach((el) => {
    el.hidden = !isAdmin;
  });

  loadSlots();
  loadMyAppointments();
  if (isAdmin) loadAdmin();
}

/* ----------------------------------------------------------------------- */
/* RF01 / RF02 - Cadastro e login                                          */
/* ----------------------------------------------------------------------- */
$("#registerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/auth/register", {
      method: "POST",
      body: {
        name: $("#regName").value,
        email: $("#regEmail").value,
        password: $("#regPassword").value,
      },
    });
    toast("Conta criada! Faca login.", "success");
    e.target.reset();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: { email: $("#loginEmail").value, password: $("#loginPassword").value },
    });
    store.set(data.access_token, data.role, data.name);
    renderAuth();
    toast(`Bem-vindo, ${data.name}!`, "success");
    e.target.reset();
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ----------------------------------------------------------------------- */
/* RF03 - Visualizar horarios disponiveis                                  */
/* ----------------------------------------------------------------------- */
let availableSlots = [];

async function loadSlots() {
  const board = $("#availabilityBoard");
  if (!store.isLogged) {
    availableSlots = [];
    board.replaceChildren(emptyState("Faca login para consultar horarios disponiveis."));
    populateBookingForm();
    return;
  }

  try {
    availableSlots = (await api("/scheduling/slots", { auth: true })) || [];
  } catch (err) {
    availableSlots = [];
    board.replaceChildren(emptyState(err.message));
    populateBookingForm();
    return;
  }

  board.replaceChildren();
  if (availableSlots.length === 0) {
    board.append(emptyState("Nenhum horario disponivel no momento."));
  } else {
    const byBarber = groupBy(availableSlots, (s) => s.barber);
    Object.keys(byBarber).forEach((barber) => {
      const row = document.createElement("article");
      row.className = "barber-row";

      const name = document.createElement("div");
      name.className = "barber-name";
      const strong = document.createElement("strong");
      strong.textContent = barber;
      const span = document.createElement("span");
      span.textContent = `${byBarber[barber].length} horarios`;
      name.append(strong, span);

      const list = document.createElement("div");
      list.className = "slot-list";
      byBarber[barber].forEach((slot) => {
        const cell = document.createElement("div");
        cell.className = "slot available";
        const t = document.createElement("strong");
        t.textContent = slot.time;
        const d = document.createElement("span");
        d.textContent = slot.date;
        cell.append(t, d);
        list.append(cell);
      });

      row.append(name, list);
      board.append(row);
    });
  }
  populateBookingForm();
}

function populateBookingForm() {
  const barberSel = $("#bookBarber");
  const barbers = [...new Set(availableSlots.map((s) => s.barber))].sort();
  barberSel.replaceChildren();

  if (!store.isLogged) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Faca login para agendar";
    barberSel.append(opt);
    updateSlotOptions();
    return;
  }

  if (barbers.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Nenhum profissional disponivel";
    barberSel.append(opt);
    updateSlotOptions();
    return;
  }

  const any = document.createElement("option");
  any.value = "";
  any.textContent = "Qualquer profissional";
  barberSel.append(any);
  barbers.forEach((b) => {
    const opt = document.createElement("option");
    opt.value = b;
    opt.textContent = b;
    barberSel.append(opt);
  });
  updateSlotOptions();
}

function updateSlotOptions() {
  const barber = $("#bookBarber").value;
  const slotSel = $("#bookSlot");
  slotSel.replaceChildren();
  const slots = availableSlots
    .filter((s) => !barber || s.barber === barber)
  if (slots.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = store.isLogged ? "Nenhum horario disponivel" : "Faca login para ver horarios";
    opt.disabled = true;
    opt.selected = true;
    slotSel.append(opt);
    return;
  }

  slots.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = `${s.barber} - ${s.date} ${s.time}`;
    slotSel.append(opt);
  });
}

$("#bookBarber").addEventListener("change", updateSlotOptions);
$("#refreshSlots").addEventListener("click", loadSlots);

/* ----------------------------------------------------------------------- */
/* RF04 - Realizar agendamento                                             */
/* ----------------------------------------------------------------------- */
$("#bookingForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!store.isLogged) {
    toast("Faca login para agendar.", "error");
    return;
  }
  const slotId = Number($("#bookSlot").value);
  if (!slotId) {
    toast("Selecione um horario.", "error");
    return;
  }
  try {
    await api("/scheduling/appointments", {
      method: "POST",
      auth: true,
      body: { slot_id: slotId, service: $("#bookService").value },
    });
    toast("Agendamento confirmado!", "success");
    await loadSlots();
    await loadMyAppointments();
    if (store.role === "admin") loadAdmin();
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ----------------------------------------------------------------------- */
/* RF05 - Cancelar agendamento + lista do cliente                          */
/* ----------------------------------------------------------------------- */
async function loadMyAppointments() {
  const container = $("#myAppointments");
  if (!store.isLogged) {
    container.replaceChildren(emptyState("Entre na sua conta para ver seus agendamentos."));
    return;
  }
  let items = [];
  try {
    items = (await api("/scheduling/appointments/me", { auth: true })) || [];
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  container.replaceChildren();
  if (items.length === 0) {
    container.append(emptyState("Nenhum agendamento realizado."));
    return;
  }
  items.forEach((appt) => {
    const card = document.createElement("article");
    const tag = document.createElement("span");
    tag.textContent = appt.service;
    const title = document.createElement("strong");
    title.textContent = `${appt.barber} - ${appt.date} ${appt.time}`;
    const statusP = document.createElement("p");
    statusP.textContent = `Status: ${appt.status}`;
    card.append(tag, title, statusP);

    if (appt.status === "ativo") {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Cancelar";
      cancel.addEventListener("click", () => cancelAppointment(appt.id));
      card.append(cancel);
    }
    container.append(card);
  });
}

async function cancelAppointment(id) {
  try {
    await api(`/scheduling/appointments/${id}`, { method: "DELETE", auth: true });
    toast("Agendamento cancelado.", "success");
    await loadMyAppointments();
    await loadSlots();
    if (store.role === "admin") loadAdmin();
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ----------------------------------------------------------------------- */
/* RF06-RF10 - Painel administrativo                                       */
/* ----------------------------------------------------------------------- */
$("#slotForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/scheduling/slots", {
      method: "POST",
      auth: true,
      body: {
        barber: $("#slotBarber").value,
        date: $("#slotDate").value,
        time: $("#slotTime").value,
      },
    });
    toast("Horario criado.", "success");
    e.target.reset();
    await loadSlots();
    loadAdmin();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadAdmin() {
  await Promise.all([loadAdminSlots(), loadAdminAppointments()]);
}

async function loadAdminSlots() {
  const container = $("#adminSlots");
  let slots = [];
  try {
    slots = (await api("/scheduling/slots?all=true", { auth: true })) || [];
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  $("#metricSlots").textContent = String(slots.filter((s) => s.available).length);

  container.replaceChildren();
  if (slots.length === 0) {
    container.append(emptyState("Nenhum horario cadastrado."));
    return;
  }
  slots.forEach((slot) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const info = document.createElement("span");
    info.textContent = `${slot.barber} - ${slot.date} ${slot.time} (${slot.available ? "livre" : "ocupado"})`;
    const del = document.createElement("button");
    del.type = "button";
    del.className = "button ghost small";
    del.textContent = "Remover";
    del.addEventListener("click", () => deleteSlot(slot.id));
    row.append(info, del);
    container.append(row);
  });
}

async function deleteSlot(id) {
  try {
    await api(`/scheduling/slots/${id}`, { method: "DELETE", auth: true });
    toast("Horario removido.", "success");
    await loadSlots();
    loadAdmin();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function loadAdminAppointments() {
  const container = $("#adminAppointments");
  let items = [];
  try {
    items = (await api("/scheduling/appointments", { auth: true })) || [];
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  const active = items.filter((a) => a.status === "ativo");
  $("#metricAppointments").textContent = String(active.length);
  $("#metricCancelled").textContent = String(items.filter((a) => a.status === "cancelado").length);

  container.replaceChildren();
  if (items.length === 0) {
    container.append(emptyState("Nenhum agendamento."));
    return;
  }
  items.forEach((appt) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const info = document.createElement("span");
    info.textContent = `${appt.user_email} | ${appt.barber} ${appt.date} ${appt.time} | ${appt.service} | ${appt.status}`;
    row.append(info);
    container.append(row);
  });
}

/* ----------------------------------------------------------------------- */
/* Utilitarios                                                             */
/* ----------------------------------------------------------------------- */
function emptyState(text) {
  const p = document.createElement("p");
  p.className = "empty-state";
  p.textContent = text;
  return p;
}

function groupBy(arr, keyFn) {
  return arr.reduce((acc, item) => {
    const key = keyFn(item);
    (acc[key] = acc[key] || []).push(item);
    return acc;
  }, {});
}

/* ----------------------------------------------------------------------- */
/* Inicializacao                                                           */
/* ----------------------------------------------------------------------- */
renderAuth();
loadSlots();
