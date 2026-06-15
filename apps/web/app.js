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
const appointmentsMessage = document.querySelector("#appointmentsMessage");
const barbeiroSelect = document.querySelector('select[name="barbeiro"]');
const dataInput = document.querySelector('input[name="data"]');
const horarioSelect = document.querySelector('select[name="horario"]');
const appointmentsMetric = document.querySelector(".admin-panel .metric");
const apiUrl =
  window.SCHEDULING_API_URL ||
  (window.location.protocol.startsWith("http") ? window.location.origin : "http://localhost:5080");
let agendamentos = [];

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

async function carregarAgendamentos() {
  const response = await fetch(`${apiUrl}/agendamentos`);

  if (!response.ok) {
    throw new Error("Nao foi possivel carregar os agendamentos.");
  }

  agendamentos = await response.json();
  return agendamentos;
}

function horarioEstaOcupado(barbeiro, data, horario) {
  return agendamentos.some(
    (agendamento) =>
      agendamento.barbeiro === barbeiro &&
      agendamento.data === data &&
      agendamento.horario === horario
  );
}

function barbeiroDisponivel(data, horario) {
  return escalas.find(
    (escala) =>
      escala.horarios.some((item) => item.hora === horario) &&
      !horarioEstaOcupado(escala.barbeiro, data, horario)
  );
}

function atualizarHorariosDoFormulario() {
  const horarios = horariosPorBarbeiro(barbeiroSelect.value);

  horarioSelect.innerHTML = "";
  horarios.forEach((hora) => {
    const qualquerProfissional = barbeiroSelect.value === "Qualquer profissional disponivel";
    const disponivel = qualquerProfissional
      ? barbeiroDisponivel(dataInput.value, hora)
      : !horarioEstaOcupado(barbeiroSelect.value, dataInput.value, hora);

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
      const cancelarButton = document.createElement("button");

      dataHorario.textContent = `${formatarData(agendamento.data)} as ${agendamento.horario}`;
      servico.textContent = agendamento.servico;
      cliente.textContent = `${agendamento.nome} com ${agendamento.barbeiro}`;
      cancelarButton.type = "button";
      cancelarButton.textContent = "Cancelar";
      cancelarButton.dataset.agendamentoId = agendamento.id;
      cancelarButton.setAttribute(
        "aria-label",
        `Cancelar agendamento de ${agendamento.nome} em ${formatarData(agendamento.data)}`
      );

      card.append(dataHorario, servico, cliente, cancelarButton);
      appointmentsList.appendChild(card);
    });
}

async function cancelarAgendamento(event) {
  const button = event.target.closest("button[data-agendamento-id]");
  if (!button) {
    return;
  }

  const agendamento = agendamentos.find((item) => item.id === button.dataset.agendamentoId);
  if (!agendamento) {
    return;
  }

  const confirmado = window.confirm(
    `Cancelar o agendamento de ${agendamento.nome} em ${formatarData(agendamento.data)} as ${agendamento.horario}?`
  );
  if (!confirmado) {
    return;
  }

  button.disabled = true;
  button.textContent = "Cancelando...";

  try {
    const response = await fetch(`${apiUrl}/agendamentos/${agendamento.id}`, {
      method: "DELETE"
    });

    if (response.status === 404) {
      await carregarAgendamentos();
      renderizarAgendamentos();
      atualizarHorariosDoFormulario();
      throw new Error("Esse agendamento ja havia sido cancelado.");
    }

    if (!response.ok) {
      throw new Error("Nao foi possivel cancelar o agendamento. Tente novamente.");
    }

    agendamentos = agendamentos.filter((item) => item.id !== agendamento.id);
    renderizarAgendamentos();
    atualizarHorariosDoFormulario();
    appointmentsMessage.textContent = "Agendamento cancelado com sucesso.";
    appointmentsMessage.className = "form-message success";
  } catch (error) {
    appointmentsMessage.textContent = error.message;
    appointmentsMessage.className = "form-message error";
    button.disabled = false;
    button.textContent = "Cancelar";
  }
}

async function realizarAgendamento(event) {
  event.preventDefault();

  if (!appointmentForm.reportValidity() || !horarioSelect.value) {
    appointmentMessage.textContent = "Preencha os dados e escolha um horario disponivel.";
    appointmentMessage.className = "form-message error";
    return;
  }

  const dados = new FormData(appointmentForm);
  const horario = dados.get("horario");
  const data = dados.get("data");
  const escolhaBarbeiro = dados.get("barbeiro");
  const escala =
    escolhaBarbeiro === "Qualquer profissional disponivel"
      ? barbeiroDisponivel(data, horario)
      : escalas.find((item) => item.barbeiro === escolhaBarbeiro);

  if (!escala || horarioEstaOcupado(escala.barbeiro, data, horario)) {
    appointmentMessage.textContent = "Esse horario acabou de ficar indisponivel. Escolha outro.";
    appointmentMessage.className = "form-message error";
    atualizarHorariosDoFormulario();
    return;
  }

  const submitButton = appointmentForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  appointmentMessage.textContent = "Salvando agendamento...";
  appointmentMessage.className = "form-message";

  try {
    const response = await fetch(`${apiUrl}/agendamentos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome: dados.get("nome").trim(),
        servico: dados.get("servico"),
        barbeiro: escala.barbeiro,
        data,
        horario
      })
    });

    if (response.status === 409) {
      await carregarAgendamentos();
      renderizarAgendamentos();
      atualizarHorariosDoFormulario();
      throw new Error("Esse horario acabou de ficar indisponivel. Escolha outro.");
    }

    if (!response.ok) {
      throw new Error("Nao foi possivel salvar o agendamento. Tente novamente.");
    }

    const novoAgendamento = await response.json();
    agendamentos.push(novoAgendamento);
    renderizarAgendamentos();
    appointmentMessage.textContent = `Agendamento confirmado com ${escala.barbeiro}.`;
    appointmentMessage.className = "form-message success";
    appointmentForm.reset();
    dataInput.value = dataLocalAtual();
    atualizarHorariosDoFormulario();
  } catch (error) {
    appointmentMessage.textContent = error.message;
    appointmentMessage.className = "form-message error";
  } finally {
    submitButton.disabled = false;
  }
}

async function iniciarAplicacao() {
  dataInput.min = dataLocalAtual();
  dataInput.value = dataInput.min;

  appointmentsList.innerHTML = '<p class="empty-state">Carregando agendamentos...</p>';

  try {
    await carregarAgendamentos();
    renderizarAgendamentos();
  } catch (error) {
    appointmentsMetric.textContent = "0";
    appointmentsList.innerHTML =
      '<p class="empty-state">Nao foi possivel carregar os agendamentos.</p>';
    appointmentMessage.textContent =
      "O servico de agendamentos esta indisponivel. Inicie a API e recarregue a pagina.";
    appointmentMessage.className = "form-message error";
  }

  atualizarHorariosDoFormulario();
}

barbeiroSelect.addEventListener("change", atualizarHorariosDoFormulario);
dataInput.addEventListener("change", atualizarHorariosDoFormulario);
appointmentForm.addEventListener("submit", realizarAgendamento);
appointmentsList.addEventListener("click", cancelarAgendamento);

iniciarAplicacao();
