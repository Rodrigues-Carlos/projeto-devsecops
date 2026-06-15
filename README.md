# Hora Marcada

Sistema web de agendamento online para barbearias e pequenos estabelecimentos, desenvolvido como projeto da disciplina de DevSecOps.

## Stack

- HTML
- CSS
- JavaScript
- ASP.NET Core
- GitHub Actions

Os agendamentos sao salvos pelo `scheduling-service` em um arquivo JSON local.

## Como executar localmente

### Pre-requisito

- .NET SDK 10

Na raiz do projeto, execute:

```powershell
dotnet run --project services/scheduling-service
```

Quando o terminal informar que a aplicacao foi iniciada, acesse:

```text
http://localhost:5080
```

O `scheduling-service` hospeda o frontend e a API, permitindo executar toda a
aplicacao com um unico comando.

> Nao abra o arquivo `apps/web/index.html` diretamente. O frontend depende da
> API em execucao para salvar e listar os agendamentos.

Para encerrar a aplicacao, pressione `Ctrl+C` no terminal.

Para verificar se a API esta funcionando, acesse:

```text
http://localhost:5080/health
```

## API de agendamentos

| Metodo | Endpoint | Descricao |
| --- | --- | --- |
| `GET` | `/health` | Verifica se o servico esta ativo |
| `GET` | `/agendamentos` | Lista os agendamentos |
| `POST` | `/agendamentos` | Cria um agendamento |
| `DELETE` | `/agendamentos/{id}` | Cancela um agendamento |

Exemplo do corpo para criacao:

```json
{
  "nome": "Maria",
  "servico": "Corte de cabelo",
  "barbeiro": "Nathan",
  "data": "2026-06-20",
  "horario": "10:00"
}
```

O servico retorna `409 Conflict` quando o barbeiro ja possui uma reserva na mesma data e horario.
Ao cancelar, retorna `204 No Content` ou `404 Not Found` quando o agendamento nao existe.

## Estrutura

```text
apps/
  web/
    index.html
    styles.css
    app.js
services/
  api-gateway/
  auth-service/
  scheduling-service/
tests/
docker/
k8s/
.github/
  workflows/
    pipeline.yaml
PLANEJAMENTO.md
```

## Planejamento

O andamento do projeto esta documentado em `PLANEJAMENTO.md`.
