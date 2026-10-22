param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CommandArgs)
$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv/Scripts/python.exe'
$localSettings = Join-Path $repoRoot 'config/local.json'
if (Test-Path -LiteralPath $localSettings) {
    $settings = Get-Content -LiteralPath $localSettings -Raw | ConvertFrom-Json
    if ($settings.python) { $pythonPath = $settings.python }
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Python environment missing. Follow RETRIEVAL.md to create .venv and install requirements.txt.'
}
$env:PYTHONIOENCODING = 'utf-8'
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $repoRoot 'src'
    & $pythonPath -m telecom_rag --repo $repoRoot @CommandArgs
    $resultCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
exit $resultCode
