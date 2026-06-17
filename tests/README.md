# Testes

A estrategia de testes segue a arquitetura de microsservicos: cada servico
possui seus proprios testes unitarios, executados de forma isolada (com SQLite
em memoria/arquivo, sem dependencia de Postgres).

```text
services/auth-service/tests/        -> RF01, RF02, RNF01, RNF10
services/scheduling-service/tests/  -> RF03..RF10, RNF10
services/api-gateway/tests/         -> autenticacao na borda (RNF01/RNF10)
```

## Executar os testes unitarios

```bash
for svc in auth-service scheduling-service api-gateway; do
  ( cd services/$svc && python -m pytest -q )
done
```

A pipeline de CI (`.github/workflows/pipeline.yaml`) executa exatamente esses
testes a cada push/pull request.

## Teste de integracao (smoke test)

Apos subir o ambiente (docker-compose ou Kubernetes), o script
[`smoke_test.sh`](smoke_test.sh) valida o fluxo completo atraves do API Gateway:
cadastro -> login -> criacao de horario (admin) -> agendamento -> cancelamento.

```bash
./tests/smoke_test.sh http://localhost:8080
```
