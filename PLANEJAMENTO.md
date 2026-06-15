# Planejamento do Projeto

## 1. Base do projeto

- [x] Definir stack principal da aplicacao web
- [x] Criar estrutura inicial do projeto
- [x] Criar pagina HTML inicial
- [x] Criar estilos basicos da interface
- [x] Criar navegacao entre telas principais

## 2. Requisitos funcionais

- [ ] RF01 - Cadastro de usuario
- [ ] RF02 - Autenticacao de usuario
- [ ] RF03 - Visualizar horarios disponiveis
- [x] RF04 - Realizar agendamento no frontend com persistencia via API REST
- [x] RF05 - Cancelar agendamento
- [ ] RF06 - Painel administrativo
- [ ] RF07 - Definir horarios
- [ ] RF08 - Editar horarios
- [ ] RF09 - Remover horarios
- [x] RF10 - Visualizar agendamentos

## 3. Testes

- [ ] Definir ferramenta de testes unitarios
- [ ] Criar testes para cadastro de usuario
- [ ] Criar testes para autenticacao
- [ ] Criar testes para visualizacao de horarios
- [ ] Criar testes para realizacao de agendamento
- [ ] Criar testes para cancelamento de agendamento
- [ ] Configurar pipeline para executar testes a cada push

## 4. Arquitetura de microsservicos

- [x] Criar aplicacao web
- [ ] Criar API Gateway
- [ ] Criar servico de autenticacao
- [x] Criar servico de agendamento
- [ ] Criar banco de dados de usuarios
- [x] Criar persistencia local de agendamentos
- [x] Fazer comunicacao entre frontend e servico de agendamento via API REST
- [x] Documentar endpoints do servico de agendamento

## 5. Docker

- [ ] Criar Dockerfile da aplicacao web
- [ ] Criar Dockerfile do API Gateway
- [ ] Criar Dockerfile do servico de autenticacao
- [ ] Criar Dockerfile do servico de agendamento
- [ ] Criar docker-compose para desenvolvimento local
- [ ] Validar execucao local dos containers

## 6. GitHub Actions

- [x] Criar workflow inicial do GitHub Actions
- [ ] Configurar runner self-hosted
- [ ] Rodar pipeline no runner self-hosted
- [ ] Adicionar etapa de instalacao de dependencias
- [ ] Adicionar etapa de testes unitarios
- [ ] Adicionar etapa de SAST
- [ ] Adicionar etapa de SCA
- [ ] Adicionar etapa de build das imagens Docker
- [ ] Adicionar etapa de entrega continua
- [ ] Adicionar etapa de implantacao continua

## 7. Kubernetes

- [ ] Criar manifests Kubernetes da aplicacao web
- [ ] Criar manifests Kubernetes do API Gateway
- [ ] Criar manifests Kubernetes do servico de autenticacao
- [ ] Criar manifests Kubernetes do servico de agendamento
- [ ] Criar Services para interconexao dos componentes
- [ ] Usar Deployments em vez de Pods estaticos
- [ ] Configurar Secrets
- [ ] Configurar politica de seguranca de Pods
- [ ] Configurar criptografia para Kubernetes Secrets
- [ ] Validar implantacao dos componentes

## 8. Seguranca de aplicacao

- [ ] Implementar criptografia/hash de senhas
- [ ] Implementar autenticacao com JWT
- [ ] Implementar controle de acesso por perfil
- [x] Validar entradas no backend
- [ ] Proteger contra SQL Injection
- [ ] Proteger contra XSS
- [ ] Implementar logs de auditoria
- [ ] Considerar as ameacas do STRIDE na implementacao
- [ ] Configurar SAST na pipeline
- [ ] Configurar SCA na pipeline

## 9. Documentacao e entrega

- [x] Atualizar README com instrucoes de uso
- [x] Atualizar documentacao da arquitetura do servico de agendamento
- [ ] Atualizar documentacao da pipeline
- [ ] Atualizar documentacao de seguranca
- [ ] Conferir criterios avaliativos
- [ ] Preparar apresentacao de ate 15 minutos
- [ ] Garantir commits de todos os integrantes
- [ ] Entregar URL do repositorio
- [ ] Entregar documento final
