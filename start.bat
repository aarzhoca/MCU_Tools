@echo off
title Nuvoton MCU Cross Reference
color 0A

echo.
echo  ================================================
echo   Nuvoton MCU Cross Reference Tool
echo  ================================================
echo.

REM -- Build frontend if dist is missing or stale --
set DIST=C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\frontend\dist\index.html
if not exist "%DIST%" (
    echo  Building frontend...
    cd /d C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\frontend
    call npm run build
    if errorlevel 1 (
        echo  ERROR: Frontend build failed. Make sure Node.js is installed.
        pause
        exit /b 1
    )
)

REM -- Open browser after 3 seconds --
echo  Starting server on http://localhost:8000
echo  Opening browser...
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM -- Start the combined backend + frontend server --
cd /d C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  Server stopped. Press any key to close.
pause
