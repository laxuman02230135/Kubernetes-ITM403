$ErrorActionPreference = 'Stop'
$taskNamespace = 'usermgmt-02230135'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskEvidenceDir = Join-Path $taskRoot 'evidence'
New-Item -ItemType Directory -Path $taskEvidenceDir -Force | Out-Null
$taskEvidencePath = Join-Path $taskEvidenceDir 'M2-persistence-test.txt'
$taskRunId = [guid]::NewGuid().ToString()

function Invoke-DatabaseSql([string]$Sql) {
    Write-Host "SQL: $Sql"
    $Sql | kubectl --context=minikube exec -i -n $taskNamespace postgres-0 -- sh -c 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    if ($LASTEXITCODE -ne 0) { throw 'Database query failed.' }
}

Start-Transcript -Path $taskEvidencePath -Force | Out-Null
try {
    Write-Host 'PostgreSQL persistence test for student 02230135'
    Write-Host "Test row ID: $taskRunId"
    Write-Host 'Before deletion: inspect the Pod and storage claim'
    $taskBeforePodJson = kubectl --context=minikube get pod postgres-0 -n $taskNamespace -o json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect database Pod.' }
    $taskBeforePod = $taskBeforePodJson | ConvertFrom-Json
    $taskBeforePvcJson = kubectl --context=minikube get pvc postgres-data-postgres-0 -n $taskNamespace -o json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect database PVC.' }
    $taskBeforePvc = $taskBeforePvcJson | ConvertFrom-Json
    if ($taskBeforePvc.status.phase -ne 'Bound') { throw 'Database PVC is not Bound.' }
    Write-Host "Original Pod UID: $($taskBeforePod.metadata.uid)"
    Write-Host "PVC UID: $($taskBeforePvc.metadata.uid)"
    Write-Host "Volume: $($taskBeforePvc.spec.volumeName)"

    Invoke-DatabaseSql @"
CREATE TABLE IF NOT EXISTS public.assignment_persistence_check (
    test_id text PRIMARY KEY,
    note text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO public.assignment_persistence_check (test_id, note)
VALUES ('$taskRunId', 'Student 02230135: saved before Pod deletion');
SELECT * FROM public.assignment_persistence_check WHERE test_id = '$taskRunId';
"@

    Write-Host 'kubectl --context=minikube delete pod postgres-0 -n usermgmt-02230135'
    kubectl --context=minikube delete pod postgres-0 -n $taskNamespace --wait=true --timeout=45s
    if ($LASTEXITCODE -ne 0) { throw 'Pod deletion did not complete.' }

    # The StatefulSet can need a moment to create its replacement Pod.
    $taskDeadline = (Get-Date).AddSeconds(120)
    do {
        $taskAfterPodJson = kubectl --context=minikube get pod postgres-0 -n $taskNamespace -o json --ignore-not-found
        if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect replacement Pod.' }
        if ($taskAfterPodJson) {
            $taskAfterPod = $taskAfterPodJson | ConvertFrom-Json
            $taskReady = @($taskAfterPod.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count -gt 0
            if ($taskAfterPod.metadata.uid -ne $taskBeforePod.metadata.uid -and $taskReady) { break }
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $taskDeadline)
    if (-not $taskReady -or $taskAfterPod.metadata.uid -eq $taskBeforePod.metadata.uid) {
        throw 'A new Ready Pod was not observed within 120 seconds.'
    }

    $taskAfterPvcJson = kubectl --context=minikube get pvc postgres-data-postgres-0 -n $taskNamespace -o json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect PVC after replacement.' }
    $taskAfterPvc = $taskAfterPvcJson | ConvertFrom-Json
    if ($taskBeforePvc.metadata.uid -ne $taskAfterPvc.metadata.uid -or $taskBeforePvc.spec.volumeName -ne $taskAfterPvc.spec.volumeName) {
        throw 'The storage claim or volume changed.'
    }
    Write-Host "Replacement Pod UID: $($taskAfterPod.metadata.uid)"
    Write-Host "Same PVC UID: $($taskAfterPvc.metadata.uid)"
    Write-Host "Same volume: $($taskAfterPvc.spec.volumeName)"
    Invoke-DatabaseSql "SELECT * FROM public.assignment_persistence_check WHERE test_id = '$taskRunId';"

    $taskCount = "SELECT count(*) FROM public.assignment_persistence_check WHERE test_id = '$taskRunId' AND note = 'Student 02230135: saved before Pod deletion';" | kubectl --context=minikube exec -i -n $taskNamespace postgres-0 -- sh -c 'exec psql -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    if ($LASTEXITCODE -ne 0 -or ($taskCount | Out-String).Trim() -ne '1') { throw 'The expected row did not survive.' }
    kubectl --context=minikube get statefulset,pod,pvc -n $taskNamespace
    Write-Host 'PASS: new Pod UID, unchanged PVC and volume, and the original row survived.'
} finally {
    Stop-Transcript | Out-Null
}
