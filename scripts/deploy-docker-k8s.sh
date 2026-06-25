#!/usr/bin/env bash
# Deploy local em Kubernetes usando as imagens do Docker da maquina.
# Funciona bem com Docker Desktop Kubernetes. Para Minikube, use deploy-minikube.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"
NS=hora-marcada
SERVICES=(auth-service scheduling-service api-gateway web)

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: docker nao encontrado no PATH." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERRO: kubectl nao encontrado no PATH." >&2
  exit 1
fi

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "ERRO: kubectl nao esta conectado a um cluster Kubernetes." >&2
  echo "Ative o Kubernetes no Docker Desktop ou selecione o contexto correto." >&2
  exit 1
fi

echo "==> 1/4 Construindo imagens no Docker local"
"$ROOT/scripts/build-images.sh" "$TAG"

echo "==> 2/4 Aplicando manifestos Kubernetes"
kubectl apply -f "$ROOT/k8s/"

echo "==> 3/4 Forcando rollout e aguardando disponibilidade"
kubectl -n "$NS" rollout restart deployment
for d in "${SERVICES[@]}"; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=240s
done
kubectl -n "$NS" rollout status statefulset/users-db --timeout=240s
kubectl -n "$NS" rollout status statefulset/appointments-db --timeout=240s

echo "==> 4/4 Recursos publicados"
kubectl -n "$NS" get pods,svc,deploy,statefulset

cat <<'MSG'

Aplicacao pronta no cluster local.
Para acessar pelo navegador, rode em outro terminal:

  kubectl -n hora-marcada port-forward svc/web 8080:80

Depois abra:

  http://localhost:8080

MSG
