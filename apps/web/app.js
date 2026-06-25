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

    const profile = document.createElement("a");
    profile.className = "button ghost";
    profile.href = "#perfil";
    profile.textContent = "Perfil";

    const out = document.createElement("button");
    out.className = "button ghost";
    out.type = "button";
    out.textContent = "Sair";
    out.addEventListener("click", () => {
      store.clear();
      renderAuth();
      window.location.hash = "inicio";
      toast("Sessao encerrada.");
    });

    area.append(hello, profile, out);
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
  document.querySelectorAll('[data-auth="logged"]').forEach((el) => {
    el.hidden = !store.isLogged;
  });
  $("#login").hidden = store.isLogged;
  if (store.isLogged) {
    $("#recuperar-conta").hidden = true;
    loadProfile();
    if (["#login", "#recuperar-conta"].includes(window.location.hash)) {
      window.location.hash = "perfil";
    }
  } else {
    $("#profileForm").reset();
  }

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
        phone: $("#regPhone").value,
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
    window.location.hash = "inicio";
    toast(`Bem-vindo, ${data.name}!`, "success");
    e.target.reset();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadProfile() {
  try {
    const profile = await api("/auth/me", { auth: true });
    $("#profileName").value = profile.name;
    $("#profileEmail").value = profile.email;
    $("#profilePhone").value = formatPhone(profile.phone);
  } catch (err) {
    if (store.isLogged) toast(err.message, "error");
  }
}

$("#profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/auth/me", {
      method: "PATCH",
      auth: true,
      body: {
        name: $("#profileName").value,
        email: $("#profileEmail").value,
        phone: $("#profilePhone").value,
      },
    });
    store.set(data.access_token, data.user.role, data.user.name);
    renderAuth();
    toast("Perfil atualizado com sucesso.", "success");
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#showRecovery").addEventListener("click", () => {
  $("#recuperar-conta").hidden = false;
  $("#recoveryEmail").value = $("#loginEmail").value;
  window.location.hash = "recuperar-conta";
  $("#recoveryEmail").focus();
});

$("#hideRecovery").addEventListener("click", hideRecovery);

function hideRecovery() {
  $("#recuperar-conta").hidden = true;
  $("#recoveryRequestForm").reset();
  $("#passwordResetForm").reset();
  $("#passwordResetForm").hidden = true;
  $("#recoveryMessage").textContent = "";
  window.location.hash = "login";
}

$("#recoveryRequestForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/auth/password-recovery/request", {
      method: "POST",
      body: { email: $("#recoveryEmail").value },
    });
    $("#recoveryMessage").textContent = data.message;
    if (data.reset_token) {
      $("#recoveryToken").value = data.reset_token;
      $("#passwordResetForm").hidden = false;
      toast("Token gerado. Defina sua nova senha.", "success");
    } else {
      $("#passwordResetForm").hidden = true;
      toast(data.message);
    }
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#passwordResetForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/auth/password-recovery/reset", {
      method: "POST",
      body: {
        token: $("#recoveryToken").value,
        new_password: $("#newPassword").value,
      },
    });
    toast(data.message, "success");
    $("#recoveryRequestForm").reset();
    $("#recoveryMessage").textContent = "";
    e.target.reset();
    e.target.hidden = true;
    hideRecovery();
  } catch (err) {
    toast(err.message, "error");
  }
});

/* ----------------------------------------------------------------------- */
/* RF03 - Visualizar horarios disponiveis                                  */
/* ----------------------------------------------------------------------- */
const DATES_PER_PAGE = 3;
let availableSlots = [];
let visibleSlots = [];
let datePageStart = 0;

async function loadSlots() {
  const board = $("#availabilityBoard");
  if (!store.isLogged) {
    availableSlots = [];
    visibleSlots = [];
    $("#scheduleNavigation").hidden = true;
    board.replaceChildren(emptyState("Faca login para consultar horarios disponiveis."));
    populateBookingForm();
    return;
  }

  try {
    availableSlots = (await api("/scheduling/slots", { auth: true })) || [];
  } catch (err) {
    availableSlots = [];
    visibleSlots = [];
    $("#scheduleNavigation").hidden = true;
    board.replaceChildren(emptyState(err.message));
    populateBookingForm();
    return;
  }

  if (availableSlots.length === 0) {
    visibleSlots = [];
    $("#scheduleNavigation").hidden = true;
    board.replaceChildren();
    board.append(emptyState("Nenhum horario disponivel no momento."));
    populateBookingForm();
    return;
  }

  const dates = availableDates();
  if (datePageStart >= dates.length) datePageStart = 0;
  configureScheduleCalendar(dates);
  renderSchedule();
}

function renderSchedule() {
  const board = $("#availabilityBoard");
  const dates = availableDates();
  const visibleDates = dates.slice(datePageStart, datePageStart + DATES_PER_PAGE);
  visibleSlots = availableSlots.filter((slot) => visibleDates.includes(slot.date));

  $("#scheduleNavigation").hidden = false;
  $("#previousDates").disabled = datePageStart === 0;
  $("#nextDates").disabled = datePageStart + DATES_PER_PAGE >= dates.length;
  $("#visibleDateRange").textContent = visibleDates.length === 1
    ? formatDate(visibleDates[0])
    : `${formatDate(visibleDates[0])} a ${formatDate(visibleDates[visibleDates.length - 1])}`;
  $("#scheduleDateJump").value = visibleDates[0];

  board.replaceChildren();
  const byBarber = groupBy(visibleSlots, (s) => s.barber);
  if (Object.keys(byBarber).length === 0) {
    board.append(emptyState("Nenhum horario disponivel neste periodo."));
  } else {
    Object.keys(byBarber).sort().forEach((barber) => {
      const row = document.createElement("article");
      row.className = "barber-row";

      const header = document.createElement("header");
      header.className = "barber-header";

      const name = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = barber;
      const span = document.createElement("span");
      span.textContent = `${byBarber[barber].length} horarios disponiveis`;
      name.append(strong, span);

      const badge = document.createElement("span");
      badge.className = "availability-badge";
      badge.textContent = "Disponivel";
      header.append(name, badge);

      const days = document.createElement("div");
      days.className = "barber-days";
      const byDate = groupBy(byBarber[barber], (s) => s.date);

      Object.keys(byDate).sort().forEach((date) => {
        const day = document.createElement("section");
        day.className = "day-group";

        const dayHeading = document.createElement("div");
        dayHeading.className = "day-heading";
        const weekday = document.createElement("strong");
        weekday.textContent = formatWeekday(date);
        const formattedDate = document.createElement("span");
        formattedDate.textContent = formatDate(date);
        dayHeading.append(weekday, formattedDate);

        const list = document.createElement("div");
        list.className = "slot-list";
        byDate[date]
          .sort((a, b) => a.time.localeCompare(b.time))
          .forEach((slot) => {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "slot available";
            cell.textContent = slot.time;
            cell.title = `Agendar com ${slot.barber} em ${formatDate(slot.date)} as ${slot.time}`;
            cell.addEventListener("click", () => selectSlotForBooking(slot));
            list.append(cell);
          });

        day.append(dayHeading, list);
        days.append(day);
      });

      row.append(header, days);
      board.append(row);
    });
  }
  populateBookingForm();
}

function availableDates() {
  return [...new Set(availableSlots.map((slot) => slot.date))].sort();
}

function configureScheduleCalendar(dates) {
  const calendar = $("#scheduleDateJump");
  calendar.min = dates[0];
  calendar.max = dates[dates.length - 1];
}

function selectSlotForBooking(slot) {
  $("#bookBarber").value = slot.barber;
  updateSlotOptions();
  $("#bookSlot").value = String(slot.id);
  $("#agendar").scrollIntoView({ behavior: "smooth", block: "start" });
  toast(`${slot.barber}, ${formatDate(slot.date)} as ${slot.time} selecionado.`, "success");
}

function populateBookingForm() {
  const barberSel = $("#bookBarber");
  const selectedBarber = barberSel.value;
  const barbers = [...new Set(visibleSlots.map((s) => s.barber))].sort();
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
  if (barbers.includes(selectedBarber)) barberSel.value = selectedBarber;
  updateSlotOptions();
}

function updateSlotOptions() {
  const barber = $("#bookBarber").value;
  const slotSel = $("#bookSlot");
  slotSel.replaceChildren();
  const slots = visibleSlots
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
    opt.textContent = `${s.barber} - ${formatDate(s.date)} as ${s.time}`;
    slotSel.append(opt);
  });
}

$("#bookBarber").addEventListener("change", updateSlotOptions);
$("#refreshSlots").addEventListener("click", loadSlots);
$("#previousDates").addEventListener("click", () => {
  datePageStart = Math.max(0, datePageStart - DATES_PER_PAGE);
  renderSchedule();
});
$("#nextDates").addEventListener("click", () => {
  const dates = availableDates();
  datePageStart = Math.min(
    Math.max(0, dates.length - 1),
    datePageStart + DATES_PER_PAGE,
  );
  renderSchedule();
});
$("#scheduleDateJump").addEventListener("change", (event) => {
  const dates = availableDates();
  const requestedDate = event.target.value;
  let index = dates.findIndex((date) => date >= requestedDate);

  if (index < 0) index = Math.max(0, dates.length - DATES_PER_PAGE);
  datePageStart = index;
  renderSchedule();

  if (dates[index] !== requestedDate) {
    toast(
      `Nao ha atendimento em ${formatDate(requestedDate)}. Exibindo ${formatDate(dates[index])}.`,
    );
  }
});

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
    title.textContent = `${appt.barber} - ${formatDate(appt.date)} as ${appt.time}`;
    const statusP = document.createElement("p");
    statusP.textContent = `Status: ${formatAppointmentStatus(appt.status)}`;
    card.append(tag, title, statusP);

    if (["ativo", "pendente", "confirmado"].includes(appt.status)) {
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
let adminSlotPage = 1;
let adminSlotPages = 1;
let adminAppointmentPage = 1;
let adminAppointmentPages = 1;

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

$("#workingHoursForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/scheduling/working-hours", {
      method: "POST",
      auth: true,
      body: {
        barber: $("#workingBarber").value,
        start_time: $("#workingStart").value,
        end_time: $("#workingEnd").value,
        interval_minutes: Number($("#workingInterval").value),
      },
    });
    toast("Funcionamento salvo e agenda anual atualizada.", "success");
    await loadSlots();
    await loadWorkingHours();
    await loadAdminSlots();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadAdmin() {
  await Promise.all([
    loadWorkingHours(),
    loadAdminSlots(),
    loadAdminAppointments(),
  ]);
}

async function loadWorkingHours() {
  const container = $("#workingHoursList");
  let rules = [];
  try {
    rules = (await api("/scheduling/working-hours", { auth: true })) || [];
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  container.replaceChildren();
  rules.forEach((rule) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "working-hours-item";
    item.textContent = `${rule.barber}: ${rule.start_time} as ${rule.end_time}, a cada ${rule.interval_minutes} min`;
    item.addEventListener("click", () => {
      $("#workingBarber").value = rule.barber;
      $("#workingStart").value = rule.start_time;
      $("#workingEnd").value = rule.end_time;
      $("#workingInterval").value = String(rule.interval_minutes);
    });
    container.append(item);
  });
}

async function loadAdminSlots() {
  const container = $("#adminSlots");
  const params = new URLSearchParams({
    page: String(adminSlotPage),
    page_size: "20",
    status: $("#slotFilterStatus").value,
  });
  const barber = $("#slotFilterBarber").value.trim();
  const date = $("#slotFilterDate").value;
  if (barber) params.set("barber", barber);
  if (date) params.set("date", date);

  let data;
  try {
    data = await api(`/scheduling/admin/slots?${params}`, { auth: true });
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  const slots = data.items || [];
  adminSlotPage = data.page;
  adminSlotPages = data.pages;
  $("#metricSlots").textContent = String(data.available_total);
  $("#slotPageInfo").textContent = `Pagina ${data.page} de ${data.pages} - ${data.total} resultados`;
  $("#previousSlotPage").disabled = data.page <= 1;
  $("#nextSlotPage").disabled = data.page >= data.pages;

  container.replaceChildren();
  if (slots.length === 0) {
    container.append(emptyState("Nenhum horario encontrado com esses filtros."));
    return;
  }
  slots.forEach((slot) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const info = document.createElement("div");
    info.className = "list-row-info";
    const title = document.createElement("strong");
    title.textContent = `${slot.barber} - ${formatDate(slot.date)} as ${slot.time}`;
    const statusLabel = document.createElement("span");
    statusLabel.className = `status-chip ${slot.available ? "free" : "busy"}`;
    statusLabel.textContent = slot.available ? "Livre" : "Ocupado";
    info.append(title, statusLabel);
    const del = document.createElement("button");
    del.type = "button";
    if (slot.available) {
      del.className = "button ghost small";
      del.textContent = "Remover";
      del.addEventListener("click", () => deleteSlot(slot.id));
    } else {
      del.className = "button danger small";
      del.textContent = "Cancelar agendamento";
      del.addEventListener("click", () => cancelAppointmentBySlot(slot));
    }
    row.append(info, del);
    container.append(row);
  });
}

async function cancelAppointmentBySlot(slot) {
  const confirmed = window.confirm(
    `Cancelar o agendamento de ${slot.barber} em ${formatDate(slot.date)} as ${slot.time}?`,
  );
  if (!confirmed) return;

  try {
    const appointment = await api(
      `/scheduling/admin/slots/${slot.id}/cancel-appointment`,
      { method: "PUT", auth: true },
    );
    toast(
      `Agendamento de ${appointment.user_name || appointment.user_email} cancelado.`,
      "success",
    );
    await Promise.all([
      loadAdminSlots(),
      loadAdminAppointments(),
      loadSlots(),
    ]);
  } catch (err) {
    toast(err.message, "error");
  }
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
  const params = new URLSearchParams({
    page: String(adminAppointmentPage),
    page_size: "20",
    status: $("#appointmentFilterStatus").value,
  });
  const email = $("#appointmentFilterEmail").value.trim();
  if (email) params.set("email", email);

  let data;
  try {
    data = await api(`/scheduling/admin/appointments?${params}`, { auth: true });
  } catch (err) {
    container.replaceChildren(emptyState(err.message));
    return;
  }
  const items = data.items || [];
  adminAppointmentPage = data.page;
  adminAppointmentPages = data.pages;
  $("#metricAppointments").textContent = String(data.active_total);
  $("#metricCancelled").textContent = String(data.cancelled_total);
  $("#appointmentPageInfo").textContent = `Pagina ${data.page} de ${data.pages} - ${data.total} resultados`;
  $("#previousAppointmentPage").disabled = data.page <= 1;
  $("#nextAppointmentPage").disabled = data.page >= data.pages;

  container.replaceChildren();
  if (items.length === 0) {
    container.append(emptyState("Nenhum agendamento encontrado."));
    return;
  }
  items.forEach((appt) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const info = document.createElement("div");
    info.className = "list-row-info";
    const title = document.createElement("strong");
    title.textContent = `${appt.barber} - ${formatDate(appt.date)} as ${appt.time}`;
    const details = document.createElement("span");
    details.textContent = `${appt.user_name || "Cliente"} - ${appt.user_email} - ${formatPhone(appt.user_phone)} - ${appt.service}`;
    const statusLabel = document.createElement("span");
    statusLabel.className = `status-chip ${appointmentStatusClass(appt.status)}`;
    statusLabel.textContent = formatAppointmentStatus(appt.status);
    info.append(title, details, statusLabel);
    if (appt.status_changed_by) {
      const audit = document.createElement("small");
      const action = appt.status === "cancelado" ? "Cancelado" : "Confirmado";
      audit.className = "audit-line";
      audit.textContent = `${action} por ${appt.status_changed_by}${appt.status_changed_at ? ` em ${formatDateTime(appt.status_changed_at)}` : ""}`;
      info.append(audit);
    }
    row.append(info);
    const actions = document.createElement("div");
    actions.className = "list-row-actions";
    if (appt.user_phone) {
      const whatsapp = document.createElement("a");
      whatsapp.className = "button whatsapp small";
      whatsapp.target = "_blank";
      whatsapp.rel = "noopener noreferrer";
      whatsapp.href = buildWhatsAppLink(appt);
      whatsapp.textContent = "WhatsApp";
      actions.append(whatsapp);
    }
    if (appt.status === "pendente") {
      const confirm = document.createElement("button");
      confirm.type = "button";
      confirm.className = "button primary small";
      confirm.textContent = "Confirmar";
      confirm.addEventListener("click", () => confirmAdminAppointment(appt.id));
      actions.append(confirm);
    }
    if (["ativo", "pendente", "confirmado"].includes(appt.status)) {
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "button danger small";
      cancel.textContent = "Cancelar";
      cancel.addEventListener("click", () => cancelAdminAppointment(appt.id));
      actions.append(cancel);
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button ghost small delete-action";
    remove.textContent = "Excluir";
    remove.addEventListener("click", () => deleteAdminAppointment(appt));
    actions.append(remove);
    row.append(actions);
    container.append(row);
  });
}

async function confirmAdminAppointment(id) {
  try {
    await api(`/scheduling/admin/appointments/${id}/confirm`, {
      method: "PUT",
      auth: true,
    });
    toast("Agendamento confirmado.", "success");
    await loadAdminAppointments();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function cancelAdminAppointment(id) {
  try {
    await api(`/scheduling/appointments/${id}`, {
      method: "DELETE",
      auth: true,
    });
    toast("Agendamento do cliente cancelado.", "success");
    await Promise.all([
      loadAdminAppointments(),
      loadAdminSlots(),
      loadSlots(),
    ]);
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteAdminAppointment(appt) {
  const confirmed = window.confirm(
    `Excluir definitivamente o agendamento de ${appt.user_email} em ${formatDate(appt.date)} as ${appt.time}?`,
  );
  if (!confirmed) return;

  try {
    await api(`/scheduling/admin/appointments/${appt.id}`, {
      method: "DELETE",
      auth: true,
    });
    toast("Agendamento excluido definitivamente.", "success");
    await Promise.all([
      loadAdminAppointments(),
      loadAdminSlots(),
      loadSlots(),
    ]);
  } catch (err) {
    toast(err.message, "error");
  }
}

$("#slotFilters").addEventListener("submit", (event) => {
  event.preventDefault();
  adminSlotPage = 1;
  loadAdminSlots();
});
$("#clearSlotFilters").addEventListener("click", () => {
  $("#slotFilters").reset();
  adminSlotPage = 1;
  loadAdminSlots();
});
$("#previousSlotPage").addEventListener("click", () => {
  if (adminSlotPage > 1) {
    adminSlotPage -= 1;
    loadAdminSlots();
  }
});
$("#nextSlotPage").addEventListener("click", () => {
  if (adminSlotPage < adminSlotPages) {
    adminSlotPage += 1;
    loadAdminSlots();
  }
});

$("#appointmentFilters").addEventListener("submit", (event) => {
  event.preventDefault();
  adminAppointmentPage = 1;
  loadAdminAppointments();
});
$("#clearAppointmentFilters").addEventListener("click", () => {
  $("#appointmentFilters").reset();
  adminAppointmentPage = 1;
  loadAdminAppointments();
});
$("#previousAppointmentPage").addEventListener("click", () => {
  if (adminAppointmentPage > 1) {
    adminAppointmentPage -= 1;
    loadAdminAppointments();
  }
});
$("#nextAppointmentPage").addEventListener("click", () => {
  if (adminAppointmentPage < adminAppointmentPages) {
    adminAppointmentPage += 1;
    loadAdminAppointments();
  }
});

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

function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

function formatWeekday(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const weekday = new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
  return weekday.charAt(0).toUpperCase() + weekday.slice(1);
}

function formatAppointmentStatus(status) {
  const labels = {
    ativo: "Confirmado",
    pendente: "Pendente",
    confirmado: "Confirmado",
    cancelado: "Cancelado",
  };
  return labels[status] || status;
}

function appointmentStatusClass(status) {
  if (status === "pendente") return "pending";
  if (status === "cancelado") return "cancelled";
  return "free";
}

function formatPhone(phone) {
  if (!phone) return "WhatsApp nao informado";
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }
  return phone;
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildWhatsAppLink(appt) {
  const phone = appt.user_phone.replace(/\D/g, "");
  const countryPhone = phone.startsWith("55") ? phone : `55${phone}`;
  const message = encodeURIComponent(
    `Ola, ${appt.user_name || "cliente"}! Seu agendamento com ${appt.barber} esta ${formatAppointmentStatus(appt.status).toLowerCase()} para ${formatDate(appt.date)} as ${appt.time}.`,
  );
  return `https://wa.me/${countryPhone}?text=${message}`;
}

function configureDateLimits() {
  const today = new Date();
  const lastDay = new Date(today);
  lastDay.setDate(lastDay.getDate() + 365);
  $("#slotDate").min = formatIsoDate(today);
  $("#slotDate").max = formatIsoDate(lastDay);
}

function formatIsoDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/* ----------------------------------------------------------------------- */
/* Inicializacao                                                           */
/* ----------------------------------------------------------------------- */
renderAuth();
loadSlots();
configureDateLimits();
