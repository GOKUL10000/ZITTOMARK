$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime-Paths.ps1')
$running = $null
try { $running = Invoke-RestMethod -Uri ($StudioUrl + '/api/health') -TimeoutSec 2 } catch {}
if (-not $running) { Write-Host 'This studio is already stopped.'; exit 0 }
if ($running.app -ne 'offline-voice-studio' -or $running.app_root -ne $PSScriptRoot) { throw 'Another app uses this address. It was left running.' }
if (-not (Test-Path -LiteralPath $PidFile)) { throw 'The process record is missing. No process was stopped.' }
$studioPid = [int](Get-Content -LiteralPath $PidFile)
if ($studioPid -ne [int]$running.pid) { throw 'The process record does not match. No process was stopped.' }
$workerScripts = @('creative_worker.py','classic_worker.py','conversion_worker.py') | ForEach-Object { Join-Path $PSScriptRoot $_ }
function Is-StudioWorker($command) {
    if (-not $command) { return $false }
    foreach ($script in $workerScripts) { if ($command.IndexOf($script,[StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true } }
    return $false
}
$processes = @(Get-CimInstance Win32_Process)
$workers = @($processes | Where-Object { $_.ParentProcessId -eq $studioPid -and $_.Name -eq 'python.exe' -and (Is-StudioWorker $_.CommandLine) })
foreach ($worker in $workers) {
    $processes | Where-Object { $_.ParentProcessId -eq $worker.ProcessId -and $_.Name -eq 'python.exe' -and (Is-StudioWorker $_.CommandLine) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $worker.ProcessId -Force -ErrorAction SilentlyContinue
}
Stop-Process -Id $studioPid -Force
$inputFolder = Join-Path $PSScriptRoot 'data\conversion-inputs'
if (Test-Path -LiteralPath $inputFolder) {
    Get-ChildItem -LiteralPath $inputFolder -File -Filter '*.wav' | ForEach-Object {
        $inputId = [guid]::Empty
        if ([guid]::TryParse($_.BaseName,[ref]$inputId)) { Remove-Item -LiteralPath $_.FullName }
    }
}
Write-Host 'Local Voice Studio stopped. Its GPU memory will be released.'
