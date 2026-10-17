param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime-Paths.ps1')
$python = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup.cmd first. The private speech runtime is not installed.' }
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$running = $null
try { $running = Invoke-RestMethod -Uri ($StudioUrl + '/api/health') -TimeoutSec 2 } catch {}
if ($running) {
    if ($running.app -ne 'offline-voice-studio' -or $running.app_root -ne $PSScriptRoot) { throw "Another app uses port $StudioPort. Stop that copy or choose OVS_PORT." }
} else {
    $process = Start-Process -FilePath $python -ArgumentList @('-u', ('"' + (Join-Path $PSScriptRoot 'server.py') + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogDir "studio-$StudioPort.log") -RedirectStandardError (Join-Path $LogDir "studio-$StudioPort-error.log") -PassThru
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 250
        if ($process.HasExited) { throw "The app could not start. Check data\logs\studio-$StudioPort-error.log." }
        try { $running = Invoke-RestMethod -Uri ($StudioUrl + '/api/health') -TimeoutSec 1 } catch { continue }
        if ($running.app_root -eq $PSScriptRoot) { break }
    }
    if (-not $running -or $running.app_root -ne $PSScriptRoot) { throw 'The studio did not finish starting. Check its local logs.' }
}
[int]$running.pid | Set-Content -LiteralPath $PidFile -Encoding ascii
Write-Host ('Local Voice Studio is ready at ' + $StudioUrl)
if (-not $NoBrowser) { Start-Process $StudioUrl }
