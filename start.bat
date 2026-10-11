@echo off
REM Revision2000 - avvio su Windows: si apre il browser con la schermata progetti.
REM Puoi anche trascinare la cartella di un progetto LaTeX su questo file.
cd /d "%~dp0"
set "PY="
where python >nul 2>nul && python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  echo Python non trovato: avvio l'installazione automatica...
  call install.bat
  exit /b
)
REM codice di uscita 3 = l'app si e' aggiornata e chiede di essere riavviata
set "R2K_LAUNCHER=1"
:run
%PY% server.py %*
if %errorlevel%==3 goto run
if errorlevel 1 pause
