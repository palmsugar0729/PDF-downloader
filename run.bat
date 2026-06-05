@echo off
chcp 65001 >nul
cd /d "%~dp0codes"
python main.py
pause
