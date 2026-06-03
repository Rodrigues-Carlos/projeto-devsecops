const horarios = [
  { hora: "09:00", barbeiro: "Nathan", status: "Disponivel" },
  { hora: "10:00", barbeiro: "Nathan", status: "Disponivel" },
  { hora: "11:00", barbeiro: "Carlos", status: "Disponivel" },
  { hora: "12:00", barbeiro: "Carlos", status: "Reservado" },
  { hora: "13:00", barbeiro: "Leonardo", status: "Disponivel" },
  { hora: "14:00", barbeiro: "Leonardo", status: "Disponivel" },
  { hora: "15:00", barbeiro: "Nathan", status: "Disponivel" },
  { hora: "16:00", barbeiro: "Carlos", status: "Reservado" },
  { hora: "17:00", barbeiro: "Leonardo", status: "Disponivel" },
  { hora: "18:00", barbeiro: "Nathan", status: "Disponivel" }
];

const grid = document.querySelector("#availabilityGrid");

horarios.forEach((horario) => {
  const button = document.createElement("button");
  const disponivel = horario.status === "Disponivel";

  button.type = "button";
  button.className = `slot ${disponivel ? "available" : "busy"}`;
  button.disabled = !disponivel;
  button.innerHTML = `<strong>${horario.hora}</strong><span>${horario.barbeiro}</span>`;
  button.setAttribute("aria-label", `${horario.hora} com ${horario.barbeiro}: ${horario.status}`);

  grid.appendChild(button);
});
