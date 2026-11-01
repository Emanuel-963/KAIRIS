param(
    [string]$InputDirectory = "data\input",
    [string]$OutputDirectory = "output",
    [switch]$Watch,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Ambiente não encontrado. Execute scripts\setup_kairis.ps1 primeiro."
}
Set-Location -LiteralPath $ProjectDir
if ($Watch) {
    & $Python run_pipeline.py --input $InputDirectory --output $OutputDirectory --watch
} else {
    $arguments = @("web_app.py", "--input", $InputDirectory, "--output", $OutputDirectory)
    if ($NoBrowser) { $arguments += "--no-open" }
    & $Python @arguments
}
