param(
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Namespace = "hora-marcada"
$Services = @("auth-service", "scheduling-service", "api-gateway", "web")

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "ERRO: '$Name' nao encontrado no PATH."
    }
}

Assert-Command "docker"
Assert-Command "kubectl"

kubectl cluster-info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "ERRO: kubectl nao esta conectado a um cluster Kubernetes. Ative o Kubernetes no Docker Desktop ou selecione o contexto correto."
}

Write-Host "==> 1/4 Construindo imagens no Docker local"
docker build -t "hora-marcada/auth-service:$Tag" (Join-Path $Root "services/auth-service")
docker build -t "hora-marcada/scheduling-service:$Tag" (Join-Path $Root "services/scheduling-service")
docker build -t "hora-marcada/api-gateway:$Tag" (Join-Path $Root "services/api-gateway")
docker build -t "hora-marcada/web:$Tag" (Join-Path $Root "apps/web")

Write-Host "==> 2/4 Aplicando manifestos Kubernetes"
kubectl apply -f (Join-Path $Root "k8s")

Write-Host "==> 3/4 Forcando rollout e aguardando disponibilidade"
kubectl -n $Namespace rollout restart deployment
foreach ($Service in $Services) {
    kubectl -n $Namespace rollout status "deployment/$Service" --timeout=240s
}
kubectl -n $Namespace rollout status statefulset/users-db --timeout=240s
kubectl -n $Namespace rollout status statefulset/appointments-db --timeout=240s

Write-Host "==> 4/4 Recursos publicados"
kubectl -n $Namespace get pods,svc,deploy,statefulset

Write-Host ""
Write-Host "Aplicacao pronta no cluster local."
Write-Host "Para acessar pelo navegador, rode em outro terminal:"
Write-Host ""
Write-Host "  kubectl -n hora-marcada port-forward svc/web 8080:80"
Write-Host ""
Write-Host "Depois abra:"
Write-Host ""
Write-Host "  http://localhost:8080"
