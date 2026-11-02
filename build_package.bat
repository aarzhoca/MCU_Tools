@echo off
setlocal EnableDelayedExpansion
title Nuvoton MCU Cross Reference - Build IT Package

echo.
echo  =====================================================
echo   Nuvoton MCU Cross Reference Tool - Package Builder
echo  =====================================================
echo.

:: ── Guard: must run from project root ─────────────────────────────────────
if not exist "Dockerfile" (
    echo  ERROR: Run this script from the project root folder
    echo         ^(the folder that contains Dockerfile^)
    echo.
    pause & exit /b 1
)

:: ── Guard: Docker must be running ─────────────────────────────────────────
echo  Checking Docker is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Docker Desktop is not running.
    echo         Please open Docker Desktop, wait for it to start, then try again.
    echo.
    pause & exit /b 1
)
echo  Docker is running.
echo.

:: ── Settings ──────────────────────────────────────────────────────────────
set IMAGE=nuvoton-mcu-xref
set OUT=nuvoton-xref-package
set ZIP=nuvoton-xref-deploy.zip

:: ── Clean previous output ─────────────────────────────────────────────────
if exist "%OUT%"  rmdir /s /q "%OUT%"
if exist "%ZIP%"  del /q "%ZIP%"
mkdir "%OUT%\backend\data"

:: ══════════════════════════════════════════════════════════════════════════
echo  [1/4]  Building Docker image...
echo         First run: 5-8 minutes.  Subsequent runs: ~1 minute.
echo.
docker build -t %IMAGE%:latest .
if errorlevel 1 (
    echo.
    echo  ERROR: Docker build failed. Check the output above.
    echo.
    pause & exit /b 1
)
echo.
echo  Build complete.
echo.

:: ══════════════════════════════════════════════════════════════════════════
echo  [2/4]  Saving image to tar file...
echo         Typically 2-4 minutes.
echo.
docker save -o "%OUT%\%IMAGE%-image.tar" %IMAGE%:latest
if errorlevel 1 (
    echo.
    echo  ERROR: docker save failed. Make sure Docker Desktop has enough disk space.
    echo.
    pause & exit /b 1
)
echo  Image saved.
echo.

:: ══════════════════════════════════════════════════════════════════════════
echo  [3/4]  Copying catalog data, config, and IT instructions...

copy /y "docker-compose.yml" "%OUT%\docker-compose.yml" >nul

if exist "backend\data\" (
    xcopy /s /e /q "backend\data\*" "%OUT%\backend\data\" >nul
)

:: Write README-IT.txt
(
echo Nuvoton MCU Cross Reference Tool - IT Setup Instructions
echo =========================================================
echo.
echo WHAT IS THIS
echo   A web tool for finding the closest Nuvoton MCU to a competitor part.
echo   It runs as a single Docker container - no database, no cloud dependency.
echo.
echo FOLDER CONTENTS
echo   nuvoton-mcu-xref-image.tar   The application ^(pre-built Docker image^)
echo   docker-compose.yml           Run configuration
echo   backend\data\                Chip catalog data files
echo   README-IT.txt                This file
echo.
echo PREREQUISITES
echo   - Docker Engine installed on the server
echo     Linux:   https://docs.docker.com/engine/install/
echo     Windows: https://docs.docker.com/desktop/install/windows-install/
echo   - Port 8000 open on the server firewall ^(or change it - see below^)
echo.
echo SETUP - run these commands once, in order
echo ------------------------------------------
echo   1. Copy this entire folder to the server
echo.
echo   2. Open a terminal in this folder
echo.
echo   3. Load the Docker image:
echo        docker load -i nuvoton-mcu-xref-image.tar
echo      ^(Takes 1-2 minutes. Done when you see "Loaded image: nuvoton-mcu-xref:latest"^)
echo.
echo   4. Start the application:
echo        docker compose up -d
echo      NOTE: do NOT add --build, the image is already loaded in step 3.
echo.
echo   5. Confirm it is running:
echo        curl http://localhost:8000/health
echo      Expected: {"status":"ok"}
echo.
echo ACCESS
echo   Users open a browser and visit:
echo     http://SERVER-IP-ADDRESS:8000
echo.
echo   To run on port 80 instead ^(no port number in the URL^):
echo     Edit docker-compose.yml, change "8000:8000" to "80:8000"
echo     Then run: docker compose up -d
echo.
echo MAINTENANCE
echo   View running containers:  docker ps
echo   View live logs:           docker compose logs -f
echo   Stop the app:             docker compose down
echo   Restart:                  docker compose restart
echo   Full reset:               docker compose down ^&^& docker compose up -d
echo.
echo DATA AND BACKUPS
echo   Chip catalog files are in .\backend\data\
echo   This folder is mapped into the container - data survives restarts.
echo   Back up this folder periodically.
echo.
echo AUTO-START ON SERVER REBOOT
echo   Pre-configured via "restart: unless-stopped" in docker-compose.yml.
echo   The app comes back automatically after any reboot or Docker restart.
echo   No extra configuration needed.
echo.
echo CHANGING THE PORT
echo   Edit docker-compose.yml and change the first number in "8000:8000"
echo   Example for port 8080:  "8080:8000"
echo   Then run: docker compose up -d
echo.
echo NEED HELP?
echo   Contact the tool owner with the output of: docker compose logs
) > "%OUT%\README-IT.txt"

echo  Files copied.
echo.

:: ══════════════════════════════════════════════════════════════════════════
echo  [4/4]  Creating zip archive...
powershell -NoProfile -Command "Compress-Archive -Path '%OUT%' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
    echo.
    echo  WARNING: Could not create zip. Send IT the '%OUT%' folder directly.
    echo.
) else (
    echo  Zip created: %ZIP%
)

:: ── Summary ───────────────────────────────────────────────────────────────
echo.
echo  =====================================================
echo   DONE
echo  =====================================================
echo.

for %%F in ("%OUT%\%IMAGE%-image.tar") do set TAR_SIZE=%%~zF
set /a TAR_MB=!TAR_SIZE! / 1048576
echo  Image file : %OUT%\%IMAGE%-image.tar  ^(!TAR_MB! MB^)

if exist "%ZIP%" (
    for %%F in ("%ZIP%") do set ZIP_SIZE=%%~zF
    set /a ZIP_MB=!ZIP_SIZE! / 1048576
    echo  Zip file   : %ZIP%  ^(!ZIP_MB! MB^)
    echo.
    echo  Send IT:  %ZIP%
) else (
    echo.
    echo  Send IT:  %OUT%\  ^(folder^)
)
echo.
echo  IT only needs Docker installed - nothing else.
echo  Full instructions are in README-IT.txt inside the package.
echo.
pause
