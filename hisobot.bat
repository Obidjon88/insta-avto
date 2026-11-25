@echo off
chcp 65001 >nul
cd /d "%~dp0"
python main.py hisobot
for /f "delims=" %%f in ('dir /b /o-d hisobotlar\hisobot_*.html') do (start "" "hisobotlar\%%f" & goto :eof)
