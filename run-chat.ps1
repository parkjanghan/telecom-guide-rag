$ErrorActionPreference = 'Stop'
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$localSettings = Join-Path $PSScriptRoot 'config/local.json'
if (Test-Path -LiteralPath $localSettings) {
    $settings = Get-Content -LiteralPath $localSettings -Raw | ConvertFrom-Json
    if ($settings.python) { $pythonPath = $settings.python }
}
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_HUB_OFFLINE = '1'
& $pythonPath -m telecom_rag.webapp
