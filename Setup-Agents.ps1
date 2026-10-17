param([string]$Python)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime-Paths.ps1')
if (-not $Python) { $Python = Join-Path $RuntimeRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run Setup.cmd first, or supply -Python with a Python 3.11 executable.' }
$agentPython = Join-Path $RuntimeRoot 'agent-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $agentPython)) {
    & $Python -m venv (Join-Path $RuntimeRoot 'agent-venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the separate agent environment.' }
}
& $agentPython -m pip install --no-deps --disable-pip-version-check --cache-dir (Join-Path $RuntimeRoot 'pip-cache') -r (Join-Path $PSScriptRoot 'requirements-agent.lock')
if ($LASTEXITCODE -ne 0) { throw 'Agent dependency installation failed.' }
& $agentPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Agent dependency check failed.' }
& $agentPython (Join-Path $PSScriptRoot 'agent_config.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not create connection examples.' }
Write-Host 'Agent support is installed. Connection examples are in data\agent-config. See docs\AGENT_INTEGRATION.md.'
