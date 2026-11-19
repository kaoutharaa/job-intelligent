# Deploy (or upgrade) the stack with the Helm chart in helm/job-intelligent.
# Usage (from the repo root):
#   .\scripts\deploy-helm.ps1           # install / upgrade
#   .\scripts\deploy-helm.ps1 -Build    # rebuild the 3 images first
# Secrets are read from k8s/secrets.env (git-ignored), never written to the chart.
param([switch]$Build)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$ns = "job-intelligent"
$release = "job-intelligent"

if (-not (Test-Path k8s/secrets.env)) {
    throw "k8s/secrets.env is missing: copy k8s/secrets.env.example and fill it in."
}

if ($Build) {
    minikube image build -t job-intelligent/api:1.0 -f Dockerfile.api .
    minikube image build -t job-intelligent/frontend:1.0 frontend
    minikube image build -t job-intelligent/airflow:1.0 -f Dockerfile.airflow .
}

# Keep the chart's copy of the schema in sync with sql/init.sql
Copy-Item sql/init.sql helm/job-intelligent/files/init.sql -Force

kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f - | Out-Null

# --- One-time migration from "kubectl apply -k ." ----------------------------
# Same names and selectors as the kustomize manifests, so Helm can adopt the
# running objects in place (the Postgres PVC data-postgres-0 is kept as is).
$owner = kubectl -n $ns get statefulset postgres --ignore-not-found -o jsonpath='{.metadata.annotations.meta\.helm\.sh/release-name}'
$exists = kubectl -n $ns get statefulset postgres --ignore-not-found -o name
if ($exists -and -not $owner) {
    Write-Host "==> Adopting resources created with kustomize" -ForegroundColor Cyan
    $objs = @(
        "configmap/app-config", "configmap/airflow-config",
        "service/postgres", "service/api", "service/frontend", "service/selenium", "service/airflow-webserver",
        "statefulset/postgres",
        "deployment/api", "deployment/frontend", "deployment/selenium",
        "deployment/airflow-webserver", "deployment/airflow-scheduler"
    )
    foreach ($o in $objs) {
        if (kubectl -n $ns get $o --ignore-not-found -o name) {
            kubectl -n $ns label $o app.kubernetes.io/managed-by=Helm --overwrite | Out-Null
            kubectl -n $ns annotate $o meta.helm.sh/release-name=$release meta.helm.sh/release-namespace=$ns --overwrite | Out-Null
        }
    }
    # Job pod templates are immutable; the chart recreates it as a Helm hook.
    kubectl -n $ns delete job airflow-init --ignore-not-found
}

# --- Secrets: k8s/secrets.env -> temporary values file -----------------------
$tmp = Join-Path ([IO.Path]::GetTempPath()) "ji-secrets-$([guid]::NewGuid()).yaml"
try {
    $lines = @("secrets:")
    foreach ($l in Get-Content k8s/secrets.env) {
        if ($l -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $v = $Matches[2].Replace("'", "''")
            $lines += "  $($Matches[1]): '$v'"
        }
    }
    $lines | Set-Content -Encoding utf8 $tmp

    Write-Host "==> helm upgrade --install $release" -ForegroundColor Cyan
    # No --wait: the airflow-init post-install hook must run while the Airflow
    # pods are still waiting for DB migrations in their initContainer.
    helm upgrade --install $release helm/job-intelligent -n $ns -f $tmp
    if ($LASTEXITCODE) { throw "helm upgrade failed" }
} finally {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

# Leftovers from kustomize (hash-suffixed generators), now replaced by the chart
kubectl -n $ns get configmap,secret -o name |
    Where-Object { $_ -match '^(configmap/postgres-init|secret/app-secrets)-[a-z0-9]{10}$' } |
    ForEach-Object { kubectl -n $ns delete $_ }

# --- Wait --------------------------------------------------------------------
kubectl -n $ns rollout status statefulset/postgres --timeout=300s
foreach ($d in "api", "frontend", "selenium", "airflow-scheduler", "airflow-webserver") {
    kubectl -n $ns rollout status deployment/$d --timeout=600s
}
helm -n $ns status $release
kubectl -n $ns get pods
