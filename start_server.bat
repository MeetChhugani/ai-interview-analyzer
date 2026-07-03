@echo off
title AI Smart Interview Analyzer Launcher
echo ===================================================
echo   Starting ADB Port Forwarding for Connected Phone
echo ===================================================
C:\Users\meetc\AppData\Local\Android\Sdk\platform-tools\adb.exe reverse tcp:8000 tcp:8000
echo.
echo ===================================================
echo   Starting Python FastAPI Backend Server
echo ===================================================
C:\Users\meetc\Desktop\ai_interview_analyzer\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir C:\Users\meetc\Desktop\ai_interview_analyzer\backend
pause
