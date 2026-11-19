# Proof of self-healing for the report. Output is also saved to restart-proof.log
#   Scenario 1: the API process crashes      -> kubelet restarts the container (RESTARTS +1)
#   Scenario 2: an API pod is deleted        -> the Deployment recreates a new pod
#   Scenario 3: the Postgres pod is deleted  -> StatefulSet recreates it, data survives (PVC)
#   Scenario 4: the Airflow scheduler pod is deleted -> recreated, DAG loaded again
$ns = "job-intelligent"
Set-Location (Split-Path $PSScriptRoot -Parent)
Start-Transcript -Path restart-proof.log -Force | Out-Null

function Show($title) {
    Write-Host "`n### $title  ($(Get-Date -Format 'HH:mm:ss'))" -ForegroundColor Cyan
    kubectl -n $ns get pods -o wide | Out-Host
}

Show "Etat initial"

# --- Scenario 1: container crash -> restart in place -------------------------
$pod = kubectl -n $ns get pods -l app=api -o jsonpath='{.items[0].metadata.name}'
$before = kubectl -n $ns get pod $pod -o jsonpath='{.status.containerStatuses[0].restartCount}'
# (SIGKILL to PID 1 from inside its own namespace is ignored by the kernel; SIGTERM stops uvicorn)
Write-Host "`n### Scenario 1: stop PID 1 (uvicorn) in $pod  (restartCount=$before)" -ForegroundColor Yellow
kubectl -n $ns exec $pod -- python -c "import os, signal; os.kill(1, signal.SIGTERM)" 2>$null | Out-Host
# Wait until the kubelet has actually counted the restart (not just a fixed sleep)
for ($i = 0; $i -lt 60; $i++) {
    $after = kubectl -n $ns get pod $pod -o jsonpath='{.status.containerStatuses[0].restartCount}'
    if ([int]$after -gt [int]$before) { break }
    Start-Sleep 2
}
kubectl -n $ns wait --for=condition=Ready pod/$pod --timeout=120s | Out-Host
Write-Host "restartCount: $before -> $after" -ForegroundColor Green
kubectl -n $ns describe pod $pod | Select-String -Pattern "Last State|Reason|Exit Code|Restart Count" | Out-Host

# --- Scenario 2: pod deletion -> replacement --------------------------------
$pod = kubectl -n $ns get pods -l app=api -o jsonpath='{.items[0].metadata.name}'
Write-Host "`n### Scenario 2: delete pod $pod" -ForegroundColor Yellow
kubectl -n $ns delete pod $pod --wait=false | Out-Host
Start-Sleep 3
Show "Juste apres la suppression (nouveau pod en creation)"
kubectl -n $ns rollout status deployment/api --timeout=180s | Out-Host
Show "Deployment revenu a 2/2"

# --- Scenario 3: database pod deletion, data persists ------------------------
Write-Host "`n### Scenario 3: write a row, delete postgres-0, read it back" -ForegroundColor Yellow
$marker = "restart-proof-$(Get-Date -Format 'yyyyMMddHHmmss')"
$sqlUser = kubectl -n $ns get cm app-config -o jsonpath='{.data.DB_USER}'
$sqlDb   = kubectl -n $ns get cm app-config -o jsonpath='{.data.DB_NAME}'
kubectl -n $ns exec postgres-0 -- psql -U $sqlUser -d $sqlDb -c "CREATE TABLE IF NOT EXISTS k8s_proof(note text, at timestamp default now()); INSERT INTO k8s_proof(note) VALUES ('$marker');" | Out-Host
$jobsBefore = kubectl -n $ns exec postgres-0 -- psql -U $sqlUser -d $sqlDb -tAc "SELECT count(*) FROM gold_jobs" 2>$null
Write-Host "gold_jobs avant suppression : $jobsBefore"
kubectl -n $ns delete pod postgres-0 | Out-Host
kubectl -n $ns wait --for=condition=Ready pod/postgres-0 --timeout=180s | Out-Host
kubectl -n $ns exec postgres-0 -- psql -U $sqlUser -d $sqlDb -c "SELECT * FROM k8s_proof WHERE note = '$marker';" | Out-Host
$jobsAfter = kubectl -n $ns exec postgres-0 -- psql -U $sqlUser -d $sqlDb -tAc "SELECT count(*) FROM gold_jobs" 2>$null
Write-Host "gold_jobs apres recreation  : $jobsAfter" -ForegroundColor Green

# --- Scenario 4: Airflow scheduler pod deletion -> replacement, DAG still loaded ---
$pod = kubectl -n $ns get pods -l app=airflow-scheduler -o jsonpath='{.items[0].metadata.name}'
Write-Host "`n### Scenario 4: delete Airflow scheduler pod $pod" -ForegroundColor Yellow
kubectl -n $ns delete pod $pod | Out-Host
kubectl -n $ns rollout status deployment/airflow-scheduler --timeout=600s | Out-Host
kubectl -n $ns wait --for=condition=Ready pod -l app=airflow-scheduler --timeout=600s | Out-Host
Write-Host "Nouveau pod : $(kubectl -n $ns get pods -l app=airflow-scheduler -o jsonpath='{.items[0].metadata.name}')"
kubectl -n $ns exec deploy/airflow-scheduler -c scheduler -- airflow dags list 2>$null | Select-String "dag_id|daily_job_scraping" | Out-Host

Show "Etat final"
kubectl -n $ns get events --sort-by=.lastTimestamp | Select-Object -Last 25 | Out-Host

Stop-Transcript | Out-Null

# Drop the transcript header/footer (machine name, Windows user, process info)
$log = Get-Content restart-proof.log
$start = ($log | Select-String -Pattern '^### Etat initial' | Select-Object -First 1).LineNumber
$end   = ($log | Select-String -Pattern '^\*{10,}' | Select-Object -Last 2 | Select-Object -First 1).LineNumber
@("Preuve de redemarrage - namespace $ns (Minikube) - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "") +
    $log[($start - 1)..($end - 2)] | Set-Content -Encoding utf8 restart-proof.log
Write-Host "`nProof saved to restart-proof.log" -ForegroundColor Green
