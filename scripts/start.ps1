param([int]$Port = 8080)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "--- Lidar Interactive Wall - Desktop Production ---"

if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating virtual environment..."
    Set-Location backend
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    Set-Location ..
}

if (-not (Test-Path "frontend\node_modules")) {
    Push-Location frontend
    npm ci
    Pop-Location
}

Push-Location backend
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $python -m pip show pywebview 2>&1 | Out-Null
$ErrorActionPreference = $prevErrorAction
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend and desktop dependencies..."
    & $python -m pip install -r requirements.txt
}
Pop-Location

Write-Host "Building production frontend..."
Push-Location frontend
npm run build
Pop-Location

Push-Location backend
$env:PYTHONPATH = (Get-Location).Path
& .\.venv\Scripts\python.exe -m app.desktop --port $Port
$exitCode = $LASTEXITCODE
Pop-Location
exit $exitCode
