#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$assignmentHosts = Join-Path $env:SystemRoot 'System32/drivers/etc/hosts'
$assignmentHostname = 'usermgmt-02230135.local'
$assignmentLines = Get-Content -LiteralPath $assignmentHosts
$assignmentMatching = @($assignmentLines | Where-Object {
    (($_ -split '#', 2)[0] -split '\s+') -contains $assignmentHostname
})
if ($assignmentMatching.Count -gt 0) {
    if ($assignmentMatching | Where-Object { $_ -notmatch '^\s*127\.0\.0\.1\s+' }) {
        throw 'This hostname already has a different address. Review the hosts file before changing it.'
    }
    Write-Host 'The localhost entry already exists.'
} else {
    $assignmentBackup = "$assignmentHosts.usermgmt-$(Get-Date -Format yyyyMMdd-HHmmss).bak"
    Copy-Item -LiteralPath $assignmentHosts -Destination $assignmentBackup
    Add-Content -LiteralPath $assignmentHosts -Value "`r`n127.0.0.1 $assignmentHostname" -Encoding ascii
    Write-Host "Added hostname. Backup: $assignmentBackup"
}
ipconfig /flushdns
Write-Host "Open http://$assignmentHostname/users while minikube tunnel is running."
