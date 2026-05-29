# Start EstateFlow API with the correct virtual environment
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PythonPath = ".\venv\Scripts\python.exe"
$PipPath = ".\venv\Scripts\pip.exe"

if (-not (Test-Path $PythonPath)) {
    $PythonPath = ".\.venv\Scripts\python.exe"
    $PipPath = ".\.venv\Scripts\pip.exe"
}

if (-not (Test-Path $PythonPath)) {
    python -m venv .venv
    $PythonPath = ".\.venv\Scripts\python.exe"
    $PipPath = ".\.venv\Scripts\pip.exe"
    & $PipPath install -r requirements.txt
}

Write-Host "Using: $((Resolve-Path $PythonPath).Path)" -ForegroundColor Green
& $PythonPath -m uvicorn app.main:app --reload --port 8000
