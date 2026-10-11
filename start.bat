@echo off
REM REVISION2000 - avvio su Windows. Si apre il browser con la schermata progetti.
REM Puoi anche trascinare una cartella LaTeX su questo file per aprirla direttamente.
cd /d "%~dp0"
where python >nul 2>nul && (python server.py %*) || (py -3 server.py %*)
pause
