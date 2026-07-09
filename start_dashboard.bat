@echo off
title EduChain Nexus Dashboard
cd /d %~dp0
echo.
echo  ============================================
echo   EduChain Nexus - Web Dashboard
echo  ============================================
echo.
echo  IMPORTANT: Do NOT open index.html directly!
echo  This script starts the server and opens your browser.
echo.
echo  Starting... (first run takes 2-4 minutes)
echo.
python server.py
if errorlevel 1 (
  echo.
  echo  ERROR: Could not start. Run: pip install -r requirements.txt
  pause
)
