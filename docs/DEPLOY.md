# Guia de Implantacao (minikube + runner self-hosted)

Este guia descreve a implantacao continua do **Hora Marcada** na VM Debian 12
usando **minikube** e um **runner self-hosted** do GitHub Actions.

## 1. Pre-requisitos na VM Debian

```bash
sudo apt-get update
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && newgrp docker
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
# minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

## 2. Iniciar o cluster

```bash
# --cni=calico habilita a aplicacao das NetworkPolicies
minikube start --driver=docker --cni=calico --memory=3500 --cpus=4
minikube addons enable ingress
minikube addons enable metrics-server   # necessario para o HPA
```

> Em VM com 4 GB, `--memory=3500` deixa folga para o sistema. Se houver pressao de
> memoria, reduza as replicas dos Deployments de 2 para 1.

## 3. Criptografia de Secrets no etcd

```bash
bash k8s/encryption/enable-encryption.sh
```

O script gera uma chave AES-CBC aleatoria, configura o kube-apiserver com
`--encryption-provider-config` e re-grava os Secrets existentes. Verifique com o
comando impresso ao final (deve aparecer o prefixo `k8s:enc:aescbc:v1:key1`).

## 4. Implantacao manual (primeira vez ou sob demanda)

```bash
./scripts/deploy-minikube.sh
```

O script constroi as imagens, carrega-as no minikube (`minikube image load`),
aplica os manifestos de `k8s/` e aguarda os rollouts.

Verifique:

```bash
kubectl -n hora-marcada get pods,svc,deploy,statefulset,hpa
kubectl -n hora-marcada get networkpolicies
```

## 5. Acessar a aplicacao

```bash
# IP do ingress
echo "http://$(minikube ip)/"
# ou via tunel (em outra aba)
minikube tunnel
```

Abra `http://<minikube-ip>/`. Login do admin inicial: `admin@horamarcada.com` /
`Admin@12345` (defina valores proprios no Secret `k8s/02-secrets.yaml`).

Teste ponta-a-ponta:

```bash
./tests/smoke_test.sh "http://$(minikube ip)"
```

## 6. Implantacao CONTINUA (runner self-hosted)

Para que cada push na branch `main` dispare a implantacao automaticamente:

1. No GitHub: **Settings > Actions > Runners > New self-hosted runner** (Linux x64).
2. Na VM, siga os comandos exibidos (download, `./config.sh`, `./run.sh`).
   Recomenda-se instalar como servico:
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```
3. Garanta que o usuario do runner tem acesso a `docker`, `kubectl` e `minikube`.
4. A partir dai, o job **deploy** da pipeline (`runs-on: self-hosted`) executa
   `./scripts/deploy-minikube.sh` a cada merge em `main`.

## 7. Fluxo completo de CI/CD

```
push/PR  ->  CI (lint+testes)  ->  SAST + SCA + secret scan
   merge em main  ->  build + push de imagens (GHCR)  ->  deploy (runner self-hosted -> minikube)
```

## Solucao de problemas

| Sintoma | Causa provavel | Acao |
|---|---|---|
| Pods `ImagePullBackOff` | imagem nao carregada no minikube | rode `./scripts/deploy-minikube.sh` (faz `minikube image load`) |
| Pod do Postgres em `CrashLoopBackOff` | permissoes do volume | confirme `PGDATA=/var/lib/postgresql/data/pgdata` e `fsGroup: 999` |
| NetworkPolicies sem efeito | CNI sem suporte | inicie com `minikube start --cni=calico` |
| HPA sem metricas | metrics-server ausente | `minikube addons enable metrics-server` |
| Ingress 404 | addon de ingress desabilitado | `minikube addons enable ingress` |
