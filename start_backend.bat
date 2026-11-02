@echo off
title Nuvoton Cross Ref — Backend API
echo Starting FastAPI backend on http://localhost:8000
echo API docs: http://localhost:8000/docs
echo Press Ctrl+C to stop.
echo.
cd /d C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
