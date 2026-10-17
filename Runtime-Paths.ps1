$RuntimeRoot = if ($env:OVS_RUNTIME_ROOT) { [IO.Path]::GetFullPath($env:OVS_RUNTIME_ROOT) } else { Join-Path $env:LOCALAPPDATA 'Zittomark\runtime' }
$StudioPort = if ($env:OVS_PORT) { [int]$env:OVS_PORT } else { 7865 }
if ($StudioPort -lt 1024 -or $StudioPort -gt 65535) { throw 'Choose a local port between 1024 and 65535.' }
$StudioUrl = "http://127.0.0.1:$StudioPort"
$LogDir = Join-Path $PSScriptRoot 'data\logs'
$PidFile = Join-Path $LogDir "studio-$StudioPort.pid"
