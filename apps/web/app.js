const escalas = [
  {
    barbeiro: "Nathan",
    periodo: "08:00 - 15:00",
    horarios: [
      { hora: "08:00", status: "Disponivel" },
      { hora: "09:00", status: "Disponivel" },
      { hora: "10:00", status: "Disponivel" },
      { hora: "11:00", status: "Disponivel" },
      { hora: "12:00", status: "Disponivel" },
      { hora: "13:00", status: "Disponivel" },
      { hora: "14:00", status: "Disponivel" },
      { hora: "15:00", status: "Disponivel" }
    ]
  },
  {
    barbeiro: "Carlos",
    periodo: "11:00 - 18:00",
    horarios: [
      { hora: "11:00", status: "Disponivel" },
      { hora: "12:00", status: "Disponivel" },
      { hora: "13:00", status: "Disponivel" },
      { hora: "14:00", status: "Disponivel" },
      { hora: "15:00", status: "Disponivel" },
      { hora: "16:00", status: "Disponivel" },
      { hora: "17:00", status: "Disponivel" },
      { hora: "18:00", status: "Disponivel" }
    ]
  },
  {
    barbeiro: "Leonardo",
    periodo: "09:00 - 16:00",
    horarios: [
      { hora: "09:00", status: "Disponivel" },
      { hora: "10:00", status: "Disponivel" },
      { hora: "11:00", status: "Disponivel" },
      { hora: "12:00", status: "Disponivel" },
      { hora: "13:00", status: "Disponivel" },
      { hora: "14:00", status: "Disponivel" },
      { hora: "15:00", status: "Disponivel" },
      { hora: "16:00", status: "Disponivel" }
    ]
  }
];

const board = document.querySelector("#availabilityBoard");
const appointmentForm = document.querySelector("#appointmentForm");
const appointmentsList = document.querySelector("#appointmentsList");
const appointmentMessage = document.querySelector("#appointmentMessage");
const barbeiroSelect = document.querySelector('select[name="barbeiro"]');
const dataInput = document.querySelector('input[name="data"]');
const horarioSelect = document.querySelector('select[name="horario"]');
const appointmentsMetric = document.querySelector(".admin-panel .metric");
const storageKey = "hora-marcada-agendamentos";

escalas.forEach((escala) => {
  const row = document.createElement("article");
  const slots = document.createElement("div");

  row.className = "barber-row";
  slots.className = "slot-list";
  row.innerHTML = `
    <div class="barber-name">
      <strong>${escala.barbeiro}</strong>
      <span>${escala.periodo}</span>
    </div>
  `;

  escala.horarios.forEach((horario) => {
    const slot = document.createElement("div");
    const disponivel = horario.status === "Disponivel";

    slot.className = `slot ${disponivel ? "available" : "busy"}`;
    slot.innerHTML = `<strong>${horario.hora}</strong><span>${horario.status}</span>`;
    slot.setAttribute("aria-label", `${horario.hora} com ${escala.barbeiro}: ${horario.status}`);

    slots.appendChild(slot);
  });

  row.appendChild(slots);
  board.appendChild(row);
});

function horariosPorBarbeiro(nomeBarbeiro) {
  if (nomeBarbeiro === "Qualquer profissional disponivel") {
    const horariosUnicos = escalas.flatMap((escala) => escala.horarios.map((horario) => horario.hora));
    return [...new Set(horariosUnicos)].sort();
  }

  const escala = escalas.find((item) => item.barbeiro === nomeBarbeiro);
  return escala ? escala.horarios.map((horario) => horario.hora) : [];
}

function carregarAgendamentos() {
  try {
    return JSON.parse(localStorage.getItem(storageKey)) || [];
  } catch {
    return [];
  }
}

function salvarAgendamentos(agendamentos) {
  localStorage.setItem(storageKey, JSON.stringify(agendamentos));
}

function horarioEstaOcupado(barbeiro, data, horario, agendamentos = carregarAgendamentos()) {
  return agendamentos.some(
    (agendamento) =>
      agendamento.barbeiro === barbeiro &&
      agendamento.data === data &&
      agendamento.horario === horario
  );
}

function barbeiroDisponivel(data, horario, agendamentos) {
  return escalas.find(
    (escala) =>
      escala.horarios.some((item) => item.hora === horario) &&
      !horarioEstaOcupado(escala.barbeiro, data, horario, agendamentos)
  );
}

function atualizarHorariosDoFormulario() {
  const horarios = horariosPorBarbeiro(barbeiroSelect.value);
  const agendamentos = carregarAgendamentos();

  horarioSelect.innerHTML = "";
  horarios.forEach((hora) => {
    const qualquerProfissional = barbeiroSelect.value === "Qualquer profissional disponivel";
    const disponivel = qualquerProfissional
      ? barbeiroDisponivel(dataInput.value, hora, agendamentos)
      : !horarioEstaOcupado(barbeiroSelect.value, dataInput.value, hora, agendamentos);

    if (!disponivel) {
      return;
    }

    const option = document.createElement("option");
    option.value = hora;
    option.textContent = hora;
    horarioSelect.appendChild(option);
  });

  if (!horarioSelect.options.length) {
    const option = document.createElement("option");
    option.textContent = "Nenhum horario disponivel";
    option.value = "";
    option.disabled = true;
    option.selected = true;
  }
}

function formatarData(data) {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(
    new Date(`${data}T00:00:00Z`)
  );
}

function dataLocalAtual() {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = String(hoje.getMonth() + 1).padStart(2, "0");
  const dia = String(hoje.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function renderizarAgendamentos() {
  const agendamentos = carregarAgendamentos();

  appointmentsList.innerHTML = "";
  appointmentsMetric.textContent = agendamentos.length;

  if (!agendamentos.length) {
    appointmentsList.innerHTML = '<p class="empty-state">Nenhum agendamento realizado.</p>';
    return;
  }

  agendamentos
    .sort((a, b) => `${a.data}${a.horario}`.localeCompare(`${b.data}${b.horario}`))
    .forEach((agendamento) => {
      const card = document.createElement("article");
      const dataHorario = document.createElement("span");
      const servico = document.createElement("strong");
      const cliente = document.createElement("p");

      dataHorario.textContent = `${formatarData(agendamento.data)} as ${agendamento.horario}`;
      servico.textContent = agendamento.servico;
      cliente.textContent = `${agendamento.nome} com ${agendamento.barbeiro}`;

      card.append(dataHorario, servico, cliente);
      appointmentsList.appendChild(card);
    });
}

function realizarAgendamento(event) {
  event.preventDefault();

  if (!appointmentForm.reportValidity() || !horarioSelect.value) {
    appointmentMessage.textContent = "Preencha os dados e escolha um horario disponivel.";
    appointmentMessage.className = "form-message error";
    return;
  }

  const dados = new FormData(appointmentForm);
  const agendamentos = carregarAgendamentos();
  const horario = dados.get("horario");
  const data = dados.get("data");
  const escolhaBarbeiro = dados.get("barbeiro");
  const escala =
    escolhaBarbeiro === "Qualquer profissional disponivel"
      ? barbeiroDisponivel(data, horario, agendamentos)
      : escalas.find((item) => item.barbeiro === escolhaBarbeiro);

  if (!escala || horarioEstaOcupado(escala.barbeiro, data, horario, agendamentos)) {
    appointmentMessage.textContent = "Esse horario acabou de ficar indisponivel. Escolha outro.";
    appointmentMessage.className = "form-message error";
    atualizarHorariosDoFormulario();
    return;
  }

  agendamentos.push({
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    nome: dados.get("nome").trim(),
    servico: dados.get("servico"),
    barbeiro: escala.barbeiro,
    data,
    horario
  });

  salvarAgendamentos(agendamentos);
  renderizarAgendamentos();
  appointmentMessage.textContent = `Agendamento confirmado com ${escala.barbeiro}.`;
  appointmentMessage.className = "form-message success";
  appointmentForm.reset();
  dataInput.value = dataLocalAtual();
  atualizarHorariosDoFormulario();
}

barbeiroSelect.addEventListener("change", atualizarHorariosDoFormulario);
dataInput.addEventListener("change", atualizarHorariosDoFormulario);
appointmentForm.addEventListener("submit", realizarAgendamento);

dataInput.min = dataLocalAtual();
dataInput.value = dataInput.min;
atualizarHorariosDoFormulario();
renderizarAgendamentos();
