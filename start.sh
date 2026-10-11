#!/usr/bin/env sh
# Revision2000 - avvio su Linux/macOS:  ./start.sh  [cartella_latex]
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo "Python 3 non trovato: avvio l'installazione automatica..."
  sh ./install.sh || exit 1
fi
exec python3 server.py "$@"
