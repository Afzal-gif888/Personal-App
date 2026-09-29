<#
.SYNOPSIS
    Stop the AgentOS windows started by start.ps1 (backend, Agent Core, frontend).
#>
$root = $PSScriptRoot
$pidFile = Join-Path $root ".agentos-pids"

$stopped = 0
if (Test-Path $pidFile) {
    foreach ($id in Get-Content $pidFile) {
        if ($id -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) {
            # /T stops the whole tree: the window, uvicorn's reloader and worker, or npm and Vite.
            taskkill /PID $id /T /F | Out-Null
            $stopped++
        }
    }
    Remove-Item $pidFile -Force
}

# Anything still holding the ports (for example a service started by hand).
foreach ($port in 8000, 8001, 5173) {
    $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($owner in $owners) {
        taskkill /PID $owner /T /F | Out-Null
        $stopped++
    }
}

Write-Host ("It's Personal stopped ({0} process tree(s))." -f $stopped)
