$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
$rootDir = Split-Path $scriptDir -Parent
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "Building Frontend..." -ForegroundColor Cyan
Set-Location $frontendDir
npm run build

Write-Host "Building Backend Executable..." -ForegroundColor Cyan
Set-Location $backendDir

# Install PyInstaller if not present
python -m pip install pyinstaller

# Run PyInstaller
python -m PyInstaller --noconfirm --name "LidarInteractiveWall" `
    --onedir `
    --windowed `
    --add-data "$frontendDir/dist;frontend/dist" `
    --add-data "data;data" `
    app/desktop.py

Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "Executable is located at: $backendDir\dist\LidarInteractiveWall\LidarInteractiveWall.exe" -ForegroundColor Green
