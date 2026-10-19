param([string]$BaseUrl = 'http://127.0.0.1:8081')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskEvidence = Join-Path $taskRoot 'evidence/M3-api-tests.txt'
$taskSuffix = [guid]::NewGuid().ToString('N').Substring(0, 10)
$taskCreatedIds = [Collections.Generic.List[long]]::new()

function Invoke-ApiCheck([string]$Method, [string]$Path, [int]$Expected, $Body = $null) {
    $taskParameters = @{
        Uri = "$BaseUrl$Path"
        Method = $Method
        SkipHttpErrorCheck = $true
        TimeoutSec = 15
    }
    if ($null -ne $Body) {
        $taskParameters.ContentType = 'application/json'
        $taskParameters.Body = ConvertTo-Json -InputObject $Body -Compress
    }
    $taskResponse = Invoke-WebRequest @taskParameters
    Write-Host "$Method $Path => $([int]$taskResponse.StatusCode)"
    Write-Host $taskResponse.Content
    if ([int]$taskResponse.StatusCode -ne $Expected) { throw "Expected HTTP $Expected." }
    if ($taskResponse.Content) { return ConvertFrom-Json -InputObject $taskResponse.Content }
}

Start-Transcript -Path $taskEvidence -Force | Out-Null
try {
    Write-Host "API integration tests through kubectl port-forward at $BaseUrl"
    Invoke-ApiCheck GET /healthz 200 | Out-Null
    Invoke-ApiCheck GET /ready 200 | Out-Null
    $taskFirst = Invoke-ApiCheck POST /users 201 @{name='Pema';email="pema-$taskSuffix@example.com"}
    $taskCreatedIds.Add($taskFirst.id)
    $taskFetched = Invoke-ApiCheck GET "/users/$($taskFirst.id)" 200
    if ($taskFetched.name -ne 'Pema') { throw 'Created user fields did not round-trip.' }
    $taskList = @(Invoke-ApiCheck GET /users 200)
    if ($taskFirst.id -notin $taskList.id) { throw 'Created user missing from list.' }
    Invoke-ApiCheck POST /users 409 @{name='Duplicate';email="PEMA-$taskSuffix@example.com"} | Out-Null
    Invoke-ApiCheck POST /users 400 @{name='';email='invalid'} | Out-Null
    $taskUpdated = Invoke-ApiCheck PUT "/users/$($taskFirst.id)" 200 @{name='Pema Updated';email="updated-$taskSuffix@example.com"}
    if ($taskUpdated.name -ne 'Pema Updated') { throw 'Update did not return the changed name.' }
    $taskFetched = Invoke-ApiCheck GET "/users/$($taskFirst.id)" 200
    if ($taskFetched.email -ne "updated-$taskSuffix@example.com") { throw 'Updated email was not persisted.' }
    $taskSecond = Invoke-ApiCheck POST /users 201 @{name='Sonam';email="sonam-$taskSuffix@example.com"}
    $taskCreatedIds.Add($taskSecond.id)
    Invoke-ApiCheck PUT "/users/$($taskSecond.id)" 409 @{name='Sonam';email="updated-$taskSuffix@example.com"} | Out-Null
    Invoke-ApiCheck DELETE "/users/$($taskFirst.id)" 204
    $taskCreatedIds.Remove($taskFirst.id) | Out-Null
    Invoke-ApiCheck GET "/users/$($taskFirst.id)" 404 | Out-Null
    Invoke-ApiCheck PUT "/users/$($taskFirst.id)" 404 @{name='Gone';email="gone-$taskSuffix@example.com"} | Out-Null
    Invoke-ApiCheck DELETE "/users/$($taskFirst.id)" 404 | Out-Null
    Invoke-ApiCheck DELETE "/users/$($taskSecond.id)" 204
    $taskCreatedIds.Remove($taskSecond.id) | Out-Null
    Write-Host 'PASS: all CRUD operations, persisted updates, duplicate protection, validation, missing users, and health endpoints.'
} finally {
    foreach ($taskId in $taskCreatedIds) {
        try { Invoke-ApiCheck DELETE "/users/$taskId" 204 | Out-Null } catch { Write-Warning "Test user $taskId needs cleanup." }
    }
    Stop-Transcript | Out-Null
}
