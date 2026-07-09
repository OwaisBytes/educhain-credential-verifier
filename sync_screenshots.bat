@echo off
cd /d %~dp0
echo Syncing screenshots to README.md for GitHub...
python scripts\sync_readme_screenshots.py
echo.
echo Next steps:
echo   git add screenshots\ README.md
echo   git commit -m "Add demo screenshots"
echo   git push
pause
