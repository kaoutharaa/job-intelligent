# Build the images inside minikube and deploy the whole stack.
# Usage (from the repo root):  .\scripts\deploy.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ns = "job-intelligent"

# The namespace is managed by Helm once deploy-helm.ps1 has run: don't fight it.
if (Get-Command helm -ErrorAction SilentlyContinue) {
    if (helm -n $ns status job-intelligent 2>$null) {
        throw "Namespace $ns is managed by the Helm release 'job-intelligent'. Use .\scripts\deploy-helm.ps1"
    }
}

# 1. Cluster (Docker Desktop gives ~7.7 GB with memory=8GB in .wslconfig)
$status = minikube status --format '{{.Host}}' 2>$null
if ($status -ne "Running") {
    Write-Host "==> Starting minikube" -ForegroundColor Cyan
    minikube start --driver=docker --cpus=4 --memory=7168
}

# 2. Secrets file (generated once, git-ignored)
function New-Hex($n) {
    $b = New-Object byte[] $n
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    -join ($b | ForEach-Object { $_.ToString("x2") })
}
if (-not (Test-Path k8s/secrets.env)) {
    Write-Host "==> Creating k8s/secrets.env with random values" -ForegroundColor Cyan
    $fb = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($fb)
    $fernet = [Convert]::ToBase64String($fb).Replace('+', '-').Replace('/', '_')
    @(
        "DB_PASS=$(New-Hex 12)"
        "JWT_SECRET=$(New-Hex 32)"
        "FERNET_KEY=$fernet"
        "SECRET_KEY=$(New-Hex 32)"
        "AIRFLOW_ADMIN_PASSWORD=$(New-Hex 8)"
        "FT_CLIENT_ID="
        "FT_CLIENT_SECRET="
    ) -join "`n" | Set-Content -NoNewline k8s/secrets.env
    Write-Warning "Fill FT_CLIENT_ID / FT_CLIENT_SECRET in k8s/secrets.env, then rerun."
}

# 3. Images, built directly into minikube's container runtime (no registry needed)
Write-Host "==> Building API image" -ForegroundColor Cyan
minikube image build -t job-intelligent/api:1.0 -f Dockerfile.api .
Write-Host "==> Building frontend image" -ForegroundColor Cyan
minikube image build -t job-intelligent/frontend:1.0 frontend
Write-Host "==> Building Airflow image (dags + scrapers baked in)" -ForegroundColor Cyan
minikube image build -t job-intelligent/airflow:1.0 -f Dockerfile.airflow .

# 4. Manifests. A Job's pod template is immutable, so the init Job is recreated
#    on each deploy (it is idempotent: db migrate + create admin if missing).
Write-Host "==> Applying manifests" -ForegroundColor Cyan
kubectl -n $ns delete job airflow-init --ignore-not-found 2>$null
kubectl apply -k .

# 5. Wait until everything is ready
kubectl -n $ns rollout status statefulset/postgres         --timeout=180s
kubectl -n $ns rollout status deployment/api               --timeout=180s
kubectl -n $ns rollout status deployment/frontend          --timeout=120s
kubectl -n $ns rollout status deployment/selenium          --timeout=300s
kubectl -n $ns wait --for=condition=complete job/airflow-init --timeout=600s
kubectl -n $ns rollout status deployment/airflow-scheduler --timeout=600s
kubectl -n $ns rollout status deployment/airflow-webserver --timeout=600s
kubectl -n $ns get pods,svc,pvc

$pw = (Get-Content k8s/secrets.env | Where-Object { $_ -like 'AIRFLOW_ADMIN_PASSWORD=*' }) -replace '^[^=]*=', ''
Write-Host "`n==> Application : minikube service frontend -n $ns" -ForegroundColor Green
Write-Host "==> Airflow     : minikube service airflow-webserver -n $ns   (admin / $pw)" -ForegroundColor Green
