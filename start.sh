#!/usr/bin/env sh
# Revision2000 - avvio su Linux/macOS:  ./start.sh  [cartella_latex]
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo "Python 3 non trovato: avvio l'installazione automatica..."
  sh ./install.sh || exit 1
fi
# codice di uscita 3 = l'app si e' aggiornata e chiede di essere riavviata
export R2K_LAUNCHER=1
while :; do
  python3 server.py "$@"
  rc=$?
  [ "$rc" -eq 3 ] || exit "$rc"
done
