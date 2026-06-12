#!/usr/bin/env bash
# Implantacao no microk8s (VM da disciplina): build das imagens, importacao no
# containerd do microk8s, aplicacao dos manifestos e rollout.
# Usado manualmente e pela pipeline (job de CD no runner self-hosted).
#
# Pre-requisitos (uma vez): usuario nos grupos 'microk8s' e 'docker'.
#   sudo usermod -a -G microk8s "$USER"; sudo usermod -a -G docker "$USER"; newgrp microk8s
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"
NS=hora-marcada
SERVICES=(auth-service scheduling-service api-gateway web)

# Usa microk8s sem sudo se o usuario estiver no grupo; senao cai para sudo.
MK="microk8s"
microk8s status >/dev/null 2>&1 || MK="sudo microk8s"

echo "==> 1/5 Habilitando addons do microk8s (dns, storage, ingress, metrics)"
$MK enable dns hostpath-storage ingress metrics-server || true
$MK status --wait-ready

echo "==> 2/5 Construindo imagens Docker"
docker build -t "hora-marcada/auth-service:$TAG"       "$ROOT/services/auth-service"
docker build -t "hora-marcada/scheduling-service:$TAG" "$ROOT/services/scheduling-service"
docker build -t "hora-marcada/api-gateway:$TAG"        "$ROOT/services/api-gateway"
docker build -t "hora-marcada/web:$TAG"                "$ROOT/apps/web"

echo "==> 3/5 Importando imagens no containerd do microk8s"
for s in "${SERVICES[@]}"; do
  docker save "hora-marcada/$s:$TAG" | $MK ctr image import -
done

echo "==> 4/5 Aplicando manifestos Kubernetes"
$MK kubectl apply -f "$ROOT/k8s/"

echo "==> 5/5 Forcando rollout e aguardando disponibilidade"
$MK kubectl -n "$NS" rollout restart deployment
for d in "${SERVICES[@]}"; do
  $MK kubectl -n "$NS" rollout status "deployment/$d" --timeout=240s
done
$MK kubectl -n "$NS" rollout status statefulset/users-db --timeout=240s
$MK kubectl -n "$NS" rollout status statefulset/appointments-db --timeout=240s

echo "==> Implantacao concluida:"
$MK kubectl -n "$NS" get pods -o wide
