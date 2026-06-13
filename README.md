# Hora Marcada

Sistema web de agendamento online para barbearias e pequenos estabelecimentos, desenvolvido como projeto da disciplina de DevSecOps.

## Stack inicial

- HTML
- CSS
- JavaScript
- GitHub Actions

Nesta primeira etapa, a aplicacao web e estatica e nao exige Docker, XAMPP, banco de dados ou instalacao de dependencias.

Os agendamentos realizados sao armazenados localmente no navegador. A integracao com API e banco de dados sera feita em uma etapa posterior.

## Como abrir localmente

Abra o arquivo abaixo no navegador:

```text
apps/web/index.html
```

## Estrutura inicial

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
