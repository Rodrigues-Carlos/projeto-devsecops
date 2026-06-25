#!/usr/bin/env bash
# Teste de integracao ponta-a-ponta atraves do API Gateway.
# Uso: ./tests/smoke_test.sh [BASE_URL]
#   BASE_URL padrao: http://localhost:8080 (web -> proxy /api -> gateway)
set -euo pipefail

BASE="${1:-http://localhost:8080}"
API="$BASE/api"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@horamarcada.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@12345}"

echo "==> Health do gateway"
curl -fsS "$API/auth/health" >/dev/null && echo "auth OK"
curl -fsS "$API/scheduling/health" >/dev/null && echo "scheduling OK"

echo "==> Login admin"
ADMIN_TOKEN=$(curl -fsS -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
echo "token admin obtido"

echo "==> Admin cria um horario (RF07)"
SLOT_ID=$(curl -fsS -X POST "$API/scheduling/slots" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"barber":"Nathan","date":"2026-12-20","time":"10:00"}' | sed -E 's/.*"id":([0-9]+).*/\1/')
echo "slot criado id=$SLOT_ID"

echo "==> Cadastro + login de cliente (RF01/RF02)"
EMAIL="cliente_$(date +%s)@example.com"
curl -fsS -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d "{\"name\":\"Cliente Teste\",\"email\":\"$EMAIL\",\"phone\":\"41999999999\",\"password\":\"senha12345\"}" >/dev/null
CLIENT_TOKEN=$(curl -fsS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"senha12345\"}" | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
echo "cliente autenticado"

echo "==> Cliente agenda (RF04)"
APPT_ID=$(curl -fsS -X POST "$API/scheduling/appointments" \
  -H "Authorization: Bearer $CLIENT_TOKEN" -H 'Content-Type: application/json' \
  -d "{\"slot_id\":$SLOT_ID,\"service\":\"Corte de cabelo\"}" | sed -E 's/.*"id":([0-9]+).*/\1/')
echo "agendamento criado id=$APPT_ID"

echo "==> Cliente cancela (RF05)"
curl -fsS -o /dev/null -w "%{http_code}\n" -X DELETE \
  "$API/scheduling/appointments/$APPT_ID" -H "Authorization: Bearer $CLIENT_TOKEN"

echo "==> SUCESSO: fluxo completo validado."
