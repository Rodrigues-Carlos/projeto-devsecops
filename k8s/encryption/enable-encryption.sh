#!/usr/bin/env bash
# Habilita criptografia de Kubernetes Secrets em repouso (etcd) no minikube.
#
# Estrategia:
#   1. Gera uma chave AES-CBC aleatoria de 32 bytes.
#   2. Copia a EncryptionConfiguration para dentro do no do minikube
#      (em /var/lib/minikube/certs, diretorio ja montado no pod do apiserver).
#   3. Reconfigura o kube-apiserver com --encryption-provider-config.
#   4. Re-grava os Secrets existentes para que passem a ser criptografados.
set -euo pipefail

CFG_LOCAL="$(mktemp)"
KEY="$(head -c 32 /dev/urandom | base64)"

cat > "$CFG_LOCAL" <<EOF
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

echo "==> Copiando EncryptionConfiguration para o no do minikube"
minikube cp "$CFG_LOCAL" /var/lib/minikube/certs/encryption-config.yaml

echo "==> Reconfigurando o kube-apiserver (reinicio do control plane)"
minikube start \
  --extra-config=apiserver.encryption-provider-config=/var/lib/minikube/certs/encryption-config.yaml

echo "==> Re-gravando Secrets existentes para criptografa-los"
kubectl get secrets --all-namespaces -o json | kubectl replace -f - >/dev/null

rm -f "$CFG_LOCAL"
echo "==> Pronto. Verifique com:"
echo "    minikube ssh -- \"sudo ETCDCTL_API=3 etcdctl \\"
echo "      --cacert /var/lib/minikube/certs/etcd/ca.crt \\"
echo "      --cert /var/lib/minikube/certs/etcd/server.crt \\"
echo "      --key /var/lib/minikube/certs/etcd/server.key \\"
echo "      get /registry/secrets/hora-marcada/hora-marcada-secrets | hexdump -C | head\""
echo "    (deve aparecer o prefixo 'k8s:enc:aescbc:v1:key1' em vez de texto claro)"
