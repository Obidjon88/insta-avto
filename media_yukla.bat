@echo off
chcp 65001 >nul
cd /d "%~dp0"
python media_yukla.py
pause
