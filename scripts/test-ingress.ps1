param([switch]$ResolveLocally)
$ErrorActionPreference = 'Stop'
$assignmentEvidence = Join-Path (Split-Path $PSScriptRoot -Parent) 'evidence/M4-ingress-tests.txt'
Start-Transcript -Path $assignmentEvidence -Force | Out-Null
try {
    kubectl --context=minikube describe ingress api -n usermgmt-02230135
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Ingress.' }
    Write-Host 'Matching hosts-file entries:'
    Select-String -LiteralPath "$env:SystemRoot/System32/drivers/etc/hosts" -Pattern 'usermgmt-02230135.local' | ForEach-Object { Write-Host $_.Line }
    $assignmentCurlArgs = @('--noproxy', '*', '--silent', '--show-error', '--max-time', '15', '-i', '-w', '\nSTATUS:%{http_code}')
    if ($ResolveLocally) {
        Write-Host 'Diagnostic mode: curl --resolve supplies the address; hosts-file setup is not verified.'
        $assignmentCurlArgs += @('--resolve', 'usermgmt-02230135.local:80:127.0.0.1')
    }
    Write-Host 'GET http://usermgmt-02230135.local/users'
    $assignmentResponse = & curl.exe @assignmentCurlArgs http://usermgmt-02230135.local/users
    Write-Host ($assignmentResponse -join "`n")
    if ($LASTEXITCODE -ne 0 -or ($assignmentResponse -join "`n") -notmatch 'STATUS:200') { throw 'Expected HTTP 200 for the matching hostname.' }
    Write-Host 'GET /users with Host: wrong-02230135.local'
    $assignmentWrong = & curl.exe --noproxy '*' --silent --show-error --max-time 15 -i -w '\nSTATUS:%{http_code}' -H 'Host: wrong-02230135.local' http://127.0.0.1/users
    Write-Host ($assignmentWrong -join "`n")
    if ($LASTEXITCODE -ne 0 -or ($assignmentWrong -join "`n") -notmatch 'STATUS:404') { throw 'Expected HTTP 404 for the unmatched hostname.' }
    Write-Host 'PASS: matching host reaches the API; unmatched host returns 404.'
} finally {
    Stop-Transcript | Out-Null
}
