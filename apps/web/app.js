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
const barbeiroSelect = document.querySelector('select[name="barbeiro"]');
const horarioSelect = document.querySelector('select[name="horario"]');

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

function atualizarHorariosDoFormulario() {
  const horarios = horariosPorBarbeiro(barbeiroSelect.value);

  horarioSelect.innerHTML = "";
  horarios.forEach((hora) => {
    const option = document.createElement("option");
    option.value = hora;
    option.textContent = hora;
    horarioSelect.appendChild(option);
  });
}

barbeiroSelect.addEventListener("change", atualizarHorariosDoFormulario);
atualizarHorariosDoFormulario();
