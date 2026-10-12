$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "--- Lidar Wall Kit - QA Checks ---"

Write-Host "`n1. Building Frontend..."
Set-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
Set-Location ..

Write-Host "`n2. Running Backend Tests..."
Set-Location backend
.venv\Scripts\python -m pytest tests/
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed" }
Set-Location ..

Write-Host "`n3. Running Soak Test (Shortened 5 mins for CI)..."
$env:SOAK_HOURS = "0.083" # ~5 mins
Set-Location backend
$backendJob = Start-Process -FilePath ".venv\Scripts\python" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8080" -PassThru -NoNewWindow
Start-Sleep -Seconds 5
.venv\Scripts\python ..\scripts\soak_test.py
$testExit = $LASTEXITCODE

Write-Host "Cleaning up backend..."
Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
Set-Location ..

if ($testExit -ne 0) { throw "Soak test failed" }

Write-Host "`nAll checks passed (Green)."
