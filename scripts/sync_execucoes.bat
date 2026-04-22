@echo off
REM Wrapper chamado pelo Windows Task Scheduler — roda a sync de execucoes.
REM Loga cada execucao em scripts\sync.log (ignorado pelo git).
REM Portavel: descobre a raiz do projeto a partir da propria localizacao.

setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."

echo. >> scripts\sync.log
echo ========== %date% %time% ========== >> scripts\sync.log
".venv\Scripts\python.exe" -X utf8 src\sync.py treinos execucoes >> scripts\sync.log 2>&1
endlocal
