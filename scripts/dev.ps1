param(
	[switch]$Desktop,
	[int]$Port = 8080,
	[switch]$Debug
)

$ErrorActionPreference = "Stop"

# Set LIDAR_FORCE_SIM
$env:LIDAR_FORCE_SIM = "0"

if ($Desktop) {
	$repoRoot = Split-Path $PSScriptRoot -Parent
	$frontendPath = Join-Path $repoRoot "frontend"
	$backendPath = Join-Path $repoRoot "backend"
	$python = Join-Path $backendPath ".venv\Scripts\python.exe"
	if (-not (Test-Path $python)) {
		throw "Backend virtual environment not found. Run scripts/start.ps1 once to install dependencies."
	}

	$env:VITE_API_TARGET = "http://127.0.0.1:$Port"
	$env:VITE_WS_TARGET = "ws://127.0.0.1:$Port"
	$vite = Start-Process -PassThru -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --host 127.0.0.1" -WorkingDirectory $frontendPath
	try {
		Push-Location $backendPath
		$env:PYTHONPATH = $backendPath
		$desktopArgs = @("--dev", "--port", "$Port")
		if ($Debug) { $desktopArgs += "--debug" }
		& $python -m app.desktop @desktopArgs
		$exitCode = $LASTEXITCODE
	}
	finally {
		Pop-Location
		if ($vite -and -not $vite.HasExited) {
			& taskkill.exe /PID $vite.Id /T /F | Out-Null
		}
	}
	exit $exitCode
}

# Start backend
Write-Host "Starting Backend..."
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-Command `"cd backend; .\.venv\Scripts\activate; uvicorn app.main:app --reload`""

# Start frontend
Write-Host "Starting Frontend..."
Start-Process -NoNewWindow -FilePath "powershell.exe" -ArgumentList "-Command `"cd frontend; npm run dev`""

Write-Host "Both services started. Press any key to stop..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup is hard with Start-Process -NoNewWindow, user can just close terminal or we suggest taskkill
Write-Host "Stopping (you might need to manually kill node/python processes if they persist)..."
