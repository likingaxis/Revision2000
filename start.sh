#!/usr/bin/env sh
# REVISION2000 - avvio su Linux/macOS:  ./start.sh  [cartella_latex]
cd "$(dirname "$0")" || exit 1
exec python3 server.py "$@"
