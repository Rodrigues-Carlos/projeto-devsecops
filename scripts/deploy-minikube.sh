#!/usr/bin/env bash
# Implantacao alternativa no minikube: constroi as imagens, carrega no cluster
# e aplica os manifestos. O deploy automatico principal usa o MicroK8s.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"
NS=hora-marcada
SERVICES=(auth-service scheduling-service api-gateway web)

echo "==> 1/4 Construindo imagens"
"$ROOT/scripts/build-images.sh" "$TAG"

echo "==> 2/4 Carregando imagens no minikube"
for s in "${SERVICES[@]}"; do
  minikube image load "hora-marcada/$s:${TAG}"
done

echo "==> 3/4 Aplicando manifestos Kubernetes"
kubectl apply -f "$ROOT/k8s/"

echo "==> 4/4 Forcando rollout e aguardando disponibilidade"
# rollout restart garante que novos Pods usem a imagem recem-carregada (tag latest).
kubectl -n "$NS" rollout restart deployment
for d in "${SERVICES[@]}"; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=180s
done
kubectl -n "$NS" rollout status statefulset/users-db --timeout=180s
kubectl -n "$NS" rollout status statefulset/appointments-db --timeout=180s

echo "==> Implantacao concluida:"
kubectl -n "$NS" get pods -o wide
