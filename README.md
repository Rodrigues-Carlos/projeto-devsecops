# Hora Marcada
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FRodrigues-Carlos%2Fprojeto-devsecops.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FRodrigues-Carlos%2Fprojeto-devsecops?ref=badge_shield)


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
| `scheduling-service` | FastAPI + SQLAlchemy | Funcionamento, agenda anual e agendamentos (RF03–RF10) |
| `users-db` / `appointments-db` | PostgreSQL 16 | Persistencia (instancias independentes) |

## Requisitos funcionais

RF01 cadastro · RF02 login · RF03 ver horarios · RF04 agendar · RF05 cancelar ·
RF06 painel admin · RF07 definir horarios · RF08 editar · RF09 remover ·
RF10 ver todos os agendamentos.

A agenda exibe tres datas por vez, mas permite navegar e reservar ao longo dos
proximos 12 meses. O administrador configura abertura, fechamento e intervalo
por profissional; domingos e horarios fora do funcionamento sao bloqueados.
As reservas iniciam como pendentes e podem ser confirmadas no painel. Nome,
e-mail e WhatsApp do cliente ficam associados ao agendamento, e confirmacoes ou
cancelamentos registram o responsavel e o horario da acao.

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

## Executar localmente (Kubernetes com Docker)

Para Docker Desktop com Kubernetes habilitado:

```bash
bash scripts/deploy-docker-k8s.sh
kubectl -n hora-marcada port-forward svc/web 8080:80
```

No Windows, sem WSL/Git Bash, use PowerShell:

```powershell
.\scripts\deploy-docker-k8s.ps1
kubectl -n hora-marcada port-forward svc/web 8080:80
```

Abra <http://localhost:8080>. As imagens sao construidas no Docker local e usadas
pelo cluster Kubernetes local.

Para Minikube com driver Docker:

```bash
minikube start --driver=docker --cni=calico --memory=3500 --cpus=4
minikube addons enable ingress
minikube addons enable metrics-server
bash scripts/deploy-minikube.sh
```

## Testes unitarios

```bash
for svc in auth-service scheduling-service api-gateway; do
  ( cd services/$svc && python -m pytest -q )
done
```

## Implantacao no Kubernetes (MicroK8s)

Guia completo em [docs/DEPLOY.md](docs/DEPLOY.md). Resumo:

```bash
sudo usermod -a -G microk8s "$USER"
sudo usermod -a -G docker "$USER"
bash scripts/deploy-microk8s.sh
bash k8s/encryption/enable-encryption-microk8s.sh
```

O MicroK8s e o ambiente principal da VM e do deploy automatico. O Minikube
continua disponivel como alternativa para outros ambientes.

## Pipeline de CI/CD

Definida em [.github/workflows/pipeline.yaml](.github/workflows/pipeline.yaml):

1. **CI** — lint (ruff) e testes (pytest) por microsservico.
2. **SAST** — Bandit, Semgrep e CodeQL.
3. **SCA** — Trivy (filesystem e imagens), pip-audit e FOSSA.
4. **Secret scanning** — Gitleaks.
5. **Entrega continua** — build e publicacao das imagens no GHCR.
6. **Implantacao continua** — MicroK8s no runner self-hosted.

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


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FRodrigues-Carlos%2Fprojeto-devsecops.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2FRodrigues-Carlos%2Fprojeto-devsecops?ref=badge_large)