#!/usr/bin/env sh
# Revision2000 - installazione dipendenze (Linux / macOS)
# Python 3 + Tk (finestra "Scegli la cartella") + LaTeX con SyncTeX e biber (opzionale).
set -e
say() { printf '  %s\n' "$*"; }
ask() { printf '  %s [s/N] ' "$1"; read -r a; [ "$a" = "s" ] || [ "$a" = "S" ] || [ "$a" = "y" ]; }

echo
say "Revision2000 - installazione dipendenze"
say "---------------------------------------"

if [ "$(uname)" = "Darwin" ]; then
  command -v brew >/dev/null || { say "Serve Homebrew: https://brew.sh"; exit 1; }
  BASE="brew install python python-tk"
  TEX="brew install --cask mactex-no-gui"
elif command -v apt-get >/dev/null; then
  BASE="sudo apt-get install -y python3 python3-tk"
  TEX="sudo apt-get install -y texlive-latex-extra texlive-lang-italian texlive-bibtex-extra biber"
elif command -v dnf >/dev/null; then
  BASE="sudo dnf install -y python3 python3-tkinter"
  TEX="sudo dnf install -y texlive-scheme-medium biber"
elif command -v pacman >/dev/null; then
  BASE="sudo pacman -S --needed --noconfirm python tk"
  TEX="sudo pacman -S --needed --noconfirm texlive-basic texlive-latexextra texlive-langitalian texlive-bibtexextra biber"
elif command -v zypper >/dev/null; then
  BASE="sudo zypper install -y python3 python3-tk"
  TEX="sudo zypper install -y texlive-scheme-medium biber"
else
  say "Gestore pacchetti non riconosciuto: installa a mano Python 3, Tk e TeX Live (vedi README)."
  exit 1
fi

if command -v python3 >/dev/null && python3 -c "import tkinter" 2>/dev/null; then
  say "[ok] Python 3 e Tk gia' installati"
else
  say "[..] Installo Python 3 e Tk:  $BASE"
  sh -c "$BASE"
fi

if command -v pdflatex >/dev/null && command -v synctex >/dev/null; then
  say "[ok] LaTeX gia' installato"
else
  say "LaTeX serve solo per i progetti .tex: per annotare PDF non e' necessario."
  if ask "Installare LaTeX (alcune centinaia di MB)?"; then
    sh -c "$TEX"
  fi
fi

chmod +x "$(dirname "$0")/start.sh" 2>/dev/null || true
echo
say "Fatto. Avvia con:  ./start.sh"
