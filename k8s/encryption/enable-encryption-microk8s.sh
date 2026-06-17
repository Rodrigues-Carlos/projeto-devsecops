#!/usr/bin/env bash
# Habilita criptografia de Kubernetes Secrets em repouso no microk8s.
# O microk8s guarda o estado em dqlite; o kube-apiserver criptografa os Secrets
# antes de persistir, via --encryption-provider-config (AES-CBC).
set -euo pipefail

ARGS_DIR=/var/snap/microk8s/current/args
KEY="$(head -c 32 /dev/urandom | base64)"

echo "==> Gravando EncryptionConfiguration em $ARGS_DIR"
sudo tee "$ARGS_DIR/encryption-config.yaml" >/dev/null <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: ${KEY}
      - identity: {}
EOF

echo "==> Adicionando a flag ao kube-apiserver (se ainda nao existir)"
if ! sudo grep -q 'encryption-provider-config' "$ARGS_DIR/kube-apiserver"; then
  echo "--encryption-provider-config=${ARGS_DIR}/encryption-config.yaml" | sudo tee -a "$ARGS_DIR/kube-apiserver" >/dev/null
fi

echo "==> Reiniciando o microk8s para aplicar"
sudo microk8s stop && sudo microk8s start
sudo microk8s status --wait-ready

echo "==> Re-gravando Secrets existentes para criptografa-los"
sudo microk8s kubectl get secrets --all-namespaces -o json | sudo microk8s kubectl replace -f - >/dev/null

echo "==> Pronto. Para verificar (deve aparecer 'k8s:enc:aescbc:v1:key1'):"
echo "    sudo microk8s kubectl get secret -n hora-marcada hora-marcada-secrets -o jsonpath='{.metadata.name}'"
echo "    (e inspecione o dqlite/datastore conforme a doc do microk8s)"
