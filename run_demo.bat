@echo off
cd /d %~dp0
echo === Compiling Smart Contract ===
python scripts\compile_contract.py
echo.
echo === Running Full DApp Demo ===
python backend\main.py
pause
