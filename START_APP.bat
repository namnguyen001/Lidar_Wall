@echo off
TITLE "Lidar Wall Kit - Backend & Frontend Server"
echo ==========================================
echo       STARTING LIDAR WALL KIT
echo ==========================================
echo.

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "scripts\start.ps1"

pause
