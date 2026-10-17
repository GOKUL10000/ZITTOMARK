param([switch]$Creative,[switch]$CheckOnly,[string]$Python)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime-Paths.ps1')
function Invoke-Checked([string]$Executable,[string[]]$ToolArguments) {
    & $Executable @ToolArguments
    if ($LASTEXITCODE -ne 0) { throw "Setup stopped because a required step failed: $Executable" }
}
if (-not [Environment]::Is64BitOperatingSystem) { throw '64-bit Windows is required.' }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows from https://git-scm.com/download/win, then run Setup.cmd again.' }
if (-not $Python) {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source -3.11 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0) { $Python = [string]$candidate }
    }
    if (-not $Python) {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command) { $Python = $command.Source }
    }
}
if (-not $Python) { throw 'Install 64-bit Python 3.11 from python.org, then run Setup.cmd again.' }
$version = & $Python -c 'import sys; print(str(sys.version_info.major)+chr(46)+str(sys.version_info.minor))'
if ($LASTEXITCODE -ne 0 -or $version -ne '3.11') { throw 'This tested setup requires Python 3.11. Install it alongside your other Python versions.' }
Write-Host 'ZITTOMARK / Local Voice Studio setup'
Write-Host "Private runtime: $RuntimeRoot"
Write-Host 'Requires an NVIDIA GPU. Models download once; speech generation is offline.'
if ($CheckOnly) { Write-Host 'Prerequisite check passed. No packages or models were installed.'; exit 0 }
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$classic = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $classic)) { Invoke-Checked $Python @('-m','venv',(Join-Path $RuntimeRoot '.venv')) }
$cache = Join-Path $RuntimeRoot 'pip-cache'
# Complete frozen environments are installed without resolving mutable VCS dependencies.
Invoke-Checked $classic @('-m','pip','install','--no-deps','--cache-dir',$cache,'--extra-index-url','https://download.pytorch.org/whl/cu128','-r',(Join-Path $PSScriptRoot 'requirements-classic.lock'))
Invoke-Checked $classic @('-m','pip','install','--no-deps','--cache-dir',$cache,'chatterbox-tts @ git+https://github.com/reenigne314/chatterbox-indic-lora.git@0cee7be98258a3085b22251e31a3379a101c1f73')
Invoke-Checked $classic @('-m','pip','check')
Invoke-Checked $classic @('-c','import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))')
if ($Creative) {
    $creativePython = Join-Path $RuntimeRoot 'qwen-venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $creativePython)) { Invoke-Checked $Python @('-m','venv',(Join-Path $RuntimeRoot 'qwen-venv')) }
    Invoke-Checked $creativePython @('-m','pip','install','--no-deps','--cache-dir',$cache,'--extra-index-url','https://download.pytorch.org/whl/cu128','-r',(Join-Path $PSScriptRoot 'requirements-creative.lock'))
    Invoke-Checked $creativePython @('-m','pip','check')
    Invoke-Checked $classic @((Join-Path $PSScriptRoot 'download_models.py'),'--creative')
    Invoke-Checked $classic @((Join-Path $PSScriptRoot 'shard_creative_model.py'))
} else { Invoke-Checked $classic @((Join-Path $PSScriptRoot 'download_models.py')) }
if ($Creative) { Invoke-Checked $classic @((Join-Path $PSScriptRoot 'doctor.py'),'--require-creative') }
else { Invoke-Checked $classic @((Join-Path $PSScriptRoot 'doctor.py')) }
Write-Host 'Setup finished. Double-click Start-Local-Voice.cmd.'
