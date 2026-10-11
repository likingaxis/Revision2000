@echo off
setlocal
title Revision2000 - installazione
echo.
echo  Revision2000 - installazione dipendenze (Windows)
echo  -------------------------------------------------
where winget >nul 2>nul || (
  echo  [!] winget non trovato. Installa "App Installer" dal Microsoft Store, oppure
  echo      Python da https://www.python.org e MiKTeX da https://miktex.org
  goto :end
)

REM ---- Python (obbligatorio)
where python >nul 2>nul && python -c "import sys" >nul 2>nul && (
  echo  [ok] Python gia' installato
) || (
  echo  [..] Installo Python 3.12
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
)

REM ---- MiKTeX (solo per i progetti LaTeX)
where pdflatex >nul 2>nul && (
  echo  [ok] LaTeX gia' installato
) || (
  echo.
  echo  LaTeX serve solo per i progetti .tex: per annotare PDF non e' necessario.
  choice /c SN /m "  Installare MiKTeX (circa 1 GB)"
  if errorlevel 2 goto :skip_tex
  winget install -e --id MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements
  REM pacchetti LaTeX mancanti scaricati automaticamente durante la compilazione
  "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value [MPM]AutoInstall=1 >nul 2>nul
)
:skip_tex

echo.
echo  Fatto. Chiudi questa finestra e avvia start.bat
echo  (se qualcosa risulta "non trovato", riavvia il PC per aggiornare il PATH).
:end
echo.
pause
