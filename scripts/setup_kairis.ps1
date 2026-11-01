param([switch]$Yes, [switch]$SkipOllama, [switch]$SkipAutoUpdate)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectDir

function Confirm-KairisAction([string]$Message) {
    if ($Yes) { return $true }
    $answer = Read-Host "$Message [s/N]"
    return $answer -match '^(s|sim|y|yes)$'
}

$PythonLauncher = $null
$PythonPrefix = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonLauncher = "py"
    $PythonPrefix = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonLauncher = "python"
}

if ($null -eq $PythonLauncher) {
    if (-not (Confirm-KairisAction "Python não encontrado. Deseja instalar Python 3.12 com winget?")) {
        throw "Python é necessário para executar o KAIRIS."
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget não encontrado. Instale Python 3.10+ manualmente e execute novamente."
    }
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
    $PythonLauncher = "py"
    $PythonPrefix = @("-3.12")
}

if (-not (Test-Path -LiteralPath ".venv")) {
    & $PythonLauncher @PythonPrefix -m venv .venv
}
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

$arguments = @("setup_kairis.py")
if ($Yes) { $arguments += "--yes" }
if ($SkipOllama) { $arguments += "--skip-ollama" }
if ($SkipAutoUpdate) { $arguments += "--skip-auto-update" }
& $VenvPython @arguments
Write-Host "KAIRIS configurado. Execute scripts\start_kairis.ps1"
