# Hora Marcada

Sistema web de **agendamento online para barbearias e pequenos estabelecimentos**,
desenvolvido como projeto da disciplina de **DevSecOps** (PUC-PR, Bacharelado em
Ciberseguranca).

O projeto implementa uma **arquitetura de microsservicos** com **API Gateway**,
comunicacao via **APIs REST**, conteinerizacao com **Docker**, orquestracao com
**Kubernetes** e uma **pipeline de CI/CD** no **GitHub Actions** com seguranca
integrada (SAST, SCA, secret scanning, FOSSA).

## Equipe

- Carlos E. Rodrigues
- Nathan M. Josviak
- Leonardo Gehr

## Arquitetura

```
                          +-------------------+
   Cliente externo  --->  |     Ingress       |
   (navegador)            +---------+---------+
                              /          \
                        /  (/)            \ (/api)
                       v                   v
                +-----------+        +--------------+
                |    web    |        | API Gateway  |  <- autenticacao JWT,
                | (nginx)   |        | (FastAPI)    |     rate limiting, rotas
                +-----------+        +------+-------+
                                     /            \
                              (REST) /              \ (REST)
                                    v                v
                        +-----------------+   +---------------------+
                        |  auth-service   |   | scheduling-service  |
                        |   (FastAPI)     |   |    (FastAPI)        |
                        +--------+--------+   +----------+----------+
                                 |                       |
                                 v                       v
                        +-----------------+   +---------------------+
                        |   users-db      |   |  appointments-db    |
                        |  (PostgreSQL)   |   |   (PostgreSQL)      |
                        +-----------------+   +---------------------+
```

Detalhes em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

| Componente | Tecnologia | Responsabilidade |
|---|---|---|
| `web` | HTML/CSS/JS + nginx | Interface de clientes e administradores |
| `api-gateway` | Python 3.12 + FastAPI | Ponto unico de entrada, valida JWT, rate limiting, roteamento |
| `auth-service` | FastAPI + SQLAlchemy | Cadastro, login (JWT), perfis (RF01, RF02) |
| `scheduling-service` | FastAPI + SQLAlchemy | Horarios e agendamentos (RF03–RF10) |
| `users-db` / `appointments-db` | PostgreSQL 16 | Persistencia (instancias independentes) |

## Requisitos funcionais

RF01 cadastro · RF02 login · RF03 ver horarios · RF04 agendar · RF05 cancelar ·
RF06 painel admin · RF07 definir horarios · RF08 editar · RF09 remover ·
RF10 ver todos os agendamentos.

## Requisitos nao funcionais (resumo)

JWT + hash bcrypt (RNF01) · alta disponibilidade via replicas (RNF02) ·
escalabilidade com microsservicos/HPA (RNF04) · logs de auditoria (RNF07) ·
validacao de entrada + ORM anti-SQLi e XSS (RNF09) · RBAC cliente/admin (RNF10).

## Executar localmente (Docker Compose)

```bash
cp docker/.env.example docker/.env       # ajuste os segredos
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build
```

- Aplicacao web: <http://localhost:8080>
- API Gateway (direto): <http://localhost:8000/health>
- Administrador inicial: `admin@horamarcada.com` / `Admin@12345` (troque em producao)

Teste de integracao ponta-a-ponta:

```bash
./tests/smoke_test.sh http://localhost:8080
```

## Testes unitarios

```bash
for svc in auth-service scheduling-service api-gateway; do
  ( cd services/$svc && python -m pytest -q )
done
```

## Implantacao no Kubernetes (minikube)

Guia completo em [docs/DEPLOY.md](docs/DEPLOY.md). Resumo:

```bash
minikube start --cni=calico
minikube addons enable ingress
minikube addons enable metrics-server
bash k8s/encryption/enable-encryption.sh   # criptografia de Secrets no etcd
./scripts/deploy-minikube.sh               # build + load + kubectl apply
```

## Pipeline de CI/CD

Definida em [.github/workflows/pipeline.yaml](.github/workflows/pipeline.yaml):

1. **CI** — lint (ruff) e testes (pytest) por microsservico.
2. **SAST** — Bandit, Semgrep e CodeQL.
3. **SCA** — Trivy (filesystem e imagens), pip-audit e FOSSA.
4. **Secret scanning** — Gitleaks.
5. **Entrega continua** — build e publicacao das imagens no GHCR.
6. **Implantacao continua** — `kubectl`/minikube em runner self-hosted.

Segredos necessarios no repositorio (Settings > Secrets and variables > Actions):

| Segredo | Uso |
|---|---|
| `FOSSA_API_KEY` | Habilita a analise FOSSA (opcional; se ausente, a etapa e ignorada) |
| `GITHUB_TOKEN` | Fornecido automaticamente (publicacao no GHCR) |

## Seguranca

- **Modelo do adversario (STRIDE):** [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md)
- **Aplicacao:** JWT, bcrypt, RBAC, validacao Pydantic, ORM (anti-SQLi), escape no
  front (anti-XSS), cabecalhos de seguranca, rate limiting, logs de auditoria.
- **Infraestrutura:** imagens nao-root, Pod Security Admission (`restricted`),
  `securityContext` endurecido, NetworkPolicies, criptografia de Secrets no etcd.

## Estrutura do repositorio

```text
apps/web/                 Frontend (HTML/CSS/JS) + nginx + Dockerfile
services/
  api-gateway/            API Gateway (FastAPI)
  auth-service/           Servico de autenticacao (FastAPI)
  scheduling-service/     Servico de agendamento (FastAPI)
docker/                   docker-compose + .env de exemplo
k8s/                      Manifestos Kubernetes + criptografia de Secrets
scripts/                  Scripts de build e deploy
tests/                    Estrategia de testes + smoke test
docs/                     Arquitetura, modelo de ameacas, guia de deploy, documento SBC
.github/workflows/        Pipeline de CI/CD
```
