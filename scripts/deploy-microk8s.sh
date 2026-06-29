#!/usr/bin/env bash
# build das imagens, importacao no
# containerd do microk8s, aplicacao dos manifestos e rollout.
# Usado manualmente e pela pipeline (job de CD no runner self-hosted).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-latest}"
NS=hora-marcada
SERVICES=(auth-service scheduling-service api-gateway web)

# O runner do GitHub Actions roda via systemd e pode nao carregar /snap/bin no PATH.
export PATH="$PATH:/snap/bin"
MK="$(command -v microk8s || true)"
if [[ -z "$MK" && -x /snap/bin/microk8s ]]; then
  MK="/snap/bin/microk8s"
fi
if [[ -z "$MK" ]]; then
  echo "ERRO: microk8s nao encontrado. Instale o MicroK8s ou adicione /snap/bin ao PATH." >&2
  exit 1
fi
if ! "$MK" status >/dev/null 2>&1; then
  echo "ERRO: usuario sem acesso ao MicroK8s ou MicroK8s indisponivel." >&2
  echo "Configure a VM uma vez e reinicie o runner:" >&2
  echo "  sudo usermod -aG microk8s,docker devsecops" >&2
  echo "  sudo chown -R devsecops ~/.kube" >&2
  echo "  sudo systemctl restart actions.runner.*.service" >&2
  exit 1
fi

echo "==> 1/5 Validando microk8s"
"$MK" status --wait-ready

echo "==> 2/5 Construindo imagens Docker"
docker build -t "hora-marcada/auth-service:$TAG"       "$ROOT/services/auth-service"
docker build -t "hora-marcada/scheduling-service:$TAG" "$ROOT/services/scheduling-service"
docker build -t "hora-marcada/api-gateway:$TAG"        "$ROOT/services/api-gateway"
docker build -t "hora-marcada/web:$TAG"                "$ROOT/apps/web"

echo "==> 3/5 Importando imagens no containerd do microk8s"
for s in "${SERVICES[@]}"; do
  docker save "hora-marcada/$s:$TAG" | "$MK" ctr image import -
done

echo "==> 4/5 Aplicando manifestos Kubernetes"
"$MK" kubectl apply -f "$ROOT/k8s/"

echo "==> 5/5 Forcando rollout e aguardando disponibilidade"
"$MK" kubectl -n "$NS" rollout restart deployment
for d in "${SERVICES[@]}"; do
  "$MK" kubectl -n "$NS" rollout status "deployment/$d" --timeout=240s
done
"$MK" kubectl -n "$NS" rollout status statefulset/users-db --timeout=240s
"$MK" kubectl -n "$NS" rollout status statefulset/appointments-db --timeout=240s

echo "==> Implantacao concluida:"
"$MK" kubectl -n "$NS" get pods -o wide
