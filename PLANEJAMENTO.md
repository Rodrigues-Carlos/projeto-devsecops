# Planejamento do Projeto

> Itens marcados com :hourglass: dependem do ambiente da VM (cluster/runner) ou
> de acoes da equipe (apresentacao, commits individuais).

## 1. Base do projeto

- [x] Definir stack principal da aplicacao web
- [x] Criar estrutura inicial do projeto
- [x] Criar pagina HTML inicial
- [x] Criar estilos basicos da interface
- [x] Criar navegacao entre telas principais

## 2. Requisitos funcionais

- [x] RF01 - Cadastro de usuario
- [x] RF02 - Autenticacao de usuario
- [x] RF03 - Visualizar horarios disponiveis
- [x] RF04 - Realizar agendamento
- [x] RF05 - Cancelar agendamento
- [x] RF06 - Painel administrativo
- [x] RF07 - Definir horarios
- [x] RF08 - Editar horarios
- [x] RF09 - Remover horarios
- [x] RF10 - Visualizar agendamentos
- [x] Configurar horario de funcionamento por profissional
- [x] Gerar agenda para os proximos 12 meses, exceto domingos
- [x] Navegar pela agenda em janelas de 3 dias
- [x] Adicionar filtros e paginacao ao painel administrativo
- [x] Permitir cancelamento administrativo de agendamentos
- [x] Permitir exclusao definitiva de agendamentos pelo administrador
- [x] Cadastrar WhatsApp do cliente
- [x] Confirmar agendamentos pelo painel administrativo
- [x] Registrar quem confirmou ou cancelou o agendamento
- [x] Cancelar agendamento diretamente pelo horario ocupado

## 3. Testes

- [x] Definir ferramenta de testes unitarios (pytest)
- [x] Criar testes para cadastro de usuario
- [x] Criar testes para autenticacao
- [x] Criar testes para visualizacao de horarios
- [x] Criar testes para realizacao de agendamento
- [x] Criar teste para concorrencia de agendamentos
- [x] Impedir exclusao de horarios com agendamentos vinculados
- [x] Validar formato e intervalo de datas e horarios
- [x] Bloquear agendamentos aos domingos e fora do funcionamento
- [x] Testar geracao anual sem duplicidade
- [x] Testar filtros, paginacao e cancelamento pelo administrador
- [x] Testar exclusao definitiva de agendamentos e liberacao do horario
- [x] Testar auditoria de confirmacao e cancelamento
- [x] Criar testes para cancelamento de agendamento
- [x] Configurar pipeline para executar testes a cada push

## 4. Arquitetura de microsservicos

- [x] Criar aplicacao web
- [x] Criar API Gateway
- [x] Criar servico de autenticacao
- [x] Criar servico de agendamento
- [x] Criar banco de dados de usuarios
- [x] Criar banco de dados de agendamentos
- [x] Fazer comunicacao entre componentes via APIs REST
- [x] Documentar endpoints principais (docs/ARCHITECTURE.md)

## 5. Docker

- [x] Criar Dockerfile da aplicacao web
- [x] Criar Dockerfile do API Gateway
- [x] Criar Dockerfile do servico de autenticacao
- [x] Criar Dockerfile do servico de agendamento
- [x] Criar docker-compose para desenvolvimento local
- [x] Validar execucao local dos containers

## 6. GitHub Actions

- [x] Criar workflow inicial do GitHub Actions
- [ ] :hourglass: Configurar runner self-hosted (na VM - ver docs/DEPLOY.md)
- [ ] :hourglass: Rodar pipeline no runner self-hosted
- [x] Adicionar etapa de instalacao de dependencias
- [x] Adicionar etapa de testes unitarios
- [x] Adicionar etapa de SAST (Bandit, Semgrep, CodeQL)
- [x] Adicionar etapa de SCA (Trivy, pip-audit, FOSSA)
- [x] Adicionar etapa de build das imagens Docker
- [x] Adicionar etapa de entrega continua (GHCR)
- [x] Adicionar etapa de implantacao continua (minikube)

## 7. Kubernetes

- [x] Criar manifests Kubernetes da aplicacao web
- [x] Criar manifests Kubernetes do API Gateway
- [x] Criar manifests Kubernetes do servico de autenticacao
- [x] Criar manifests Kubernetes do servico de agendamento
- [x] Criar Services para interconexao dos componentes
- [x] Usar Deployments em vez de Pods estaticos
- [x] Configurar Secrets
- [x] Configurar politica de seguranca de Pods (Pod Security Admission + NetworkPolicies)
- [x] Configurar criptografia para Kubernetes Secrets (etcd, AES-CBC)
- [ ] :hourglass: Validar implantacao dos componentes (requer cluster na VM)

## 8. Seguranca de aplicacao

- [x] Implementar criptografia/hash de senhas (bcrypt)
- [x] Implementar autenticacao com JWT
- [x] Implementar controle de acesso por perfil (RBAC)
- [x] Validar entradas no backend (Pydantic)
- [x] Proteger contra SQL Injection (ORM/consultas parametrizadas)
- [x] Proteger contra XSS (escape no front + cabecalhos de seguranca)
- [x] Implementar logs de auditoria
- [x] Considerar as ameacas do STRIDE na implementacao (docs/THREAT_MODEL.md)
- [x] Configurar SAST na pipeline
- [x] Configurar SCA na pipeline

## 9. Documentacao e entrega

- [x] Atualizar README com instrucoes de uso
- [x] Atualizar documentacao da arquitetura
- [x] Atualizar documentacao da pipeline
- [x] Atualizar documentacao de seguranca
- [x] Conferir criterios avaliativos
- [ ] :hourglass: Preparar apresentacao de ate 15 minutos (equipe)
- [ ] :hourglass: Garantir commits de todos os integrantes (equipe)
- [x] Entregar URL do repositorio
- [x] Entregar documento final (docs/documento-sbc.docx)
