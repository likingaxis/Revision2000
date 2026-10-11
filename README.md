# REVISION2000

Revisione veloce di tesi e documenti: **annoti il PDF nel browser**, ottieni un file di revisioni
(`REVIEW.md` + `review.json`) pronto da dare a un assistente AI (Claude Code o simili), che applica
le modifiche al sorgente.

- **Progetti LaTeX**: ogni nota viene collegata al file `.tex`, alla riga e al **testo esatto del sorgente**
  (SyncTeX + allineamento del testo). Puoi anche compilare dall'app.
- **PDF qualsiasi** (anche senza sorgenti, es. export da Word): le note vengono ancorate a pagina e testo.

Funziona su **Windows, Linux e macOS**. Nessun pacchetto Python da installare.

---

## 1. Installazione

### Automatica (consigliata)

| Sistema | Cosa fare |
|---|---|
| Windows | doppio clic su **`install.bat`** (usa `winget`: installa Python e, se vuoi, MiKTeX) |
| Linux / macOS | `sh install.sh` (riconosce apt, dnf, pacman, zypper o Homebrew; chiede la password per `sudo`) |

LaTeX è facoltativo e lo script chiede prima di installarlo. Se manca Python, `start.bat` e
`start.sh` avviano l'installazione da soli. Se nella home manca qualche strumento LaTeX, il
pulsante *Copia il comando per installare LaTeX* copia il comando giusto per il tuo sistema.

### Manuale

### Requisiti

| Cosa | Serve per | Obbligatorio |
|---|---|---|
| Python ≥ 3.8 | far girare l'app | sì |
| Browser moderno + connessione internet | visualizzare il PDF (pdf.js caricato da CDN) | sì |
| Distribuzione LaTeX (`pdflatex`, `synctex`, `bibtex`/`biber`) | progetti LaTeX: collegamento al sorgente e compilazione | solo per LaTeX |

Per **annotare solo PDF** bastano Python e un browser.

### Windows

1. **Python**: installalo da <https://www.python.org/downloads/> e spunta *"Add python.exe to PATH"*.
   In alternativa: `winget install Python.Python.3.12`
2. **LaTeX (opzionale)**: [MiKTeX](https://miktex.org/download). Nella MiKTeX Console imposta
   *"Install missing packages on-the-fly: Yes"*. `latexmk`/Perl **non** servono.
3. Scarica/copia la cartella `REVISION2000`.

### Linux

```bash
# Debian / Ubuntu / Mint
sudo apt install python3 python3-tk texlive-latex-extra texlive-lang-italian texlive-bibtex-extra biber

# Fedora
sudo dnf install python3 python3-tkinter texlive-scheme-medium biber

# Arch
sudo pacman -S python tk texlive-basic texlive-latexextra texlive-langitalian texlive-bibtexextra biber
```

`python3-tk` serve per la finestra "Scegli la cartella" (in alternativa va bene `zenity` o `kdialog`;
se non c'è nessuno dei tre l'app mostra un esploratore interno). `synctex` è incluso in TeX Live. Il pacchetto `texlive-lang-italian` serve solo per documenti in italiano.
Se il documento usa pacchetti particolari e la compilazione segnala `File 'xyz.sty' not found`,
installa `texlive-full` (Debian/Ubuntu) o `texlive-scheme-full` (Fedora).

### macOS

```bash
brew install python
brew install --cask mactex-no-gui
```

### Verifica

```bash
python3 --version
pdflatex --version
synctex help
```

Su Windows usa `python` al posto di `python3`. La schermata iniziale dell'app mostra comunque quali
strumenti LaTeX sono stati trovati (✓/✗).

---

## 2. Avvio

- **Windows**: doppio clic su `start.bat` (puoi anche trascinare la cartella della tesi su `start.bat`).
- **Linux/macOS**:
  ```bash
  ./start.sh
  ```
  oppure, per aprire direttamente un progetto LaTeX:
  ```bash
  ./start.sh ~/tesi
  ```

Si apre il browser su <http://127.0.0.1:8765>. Altre opzioni:

```bash
python3 server.py [cartella] --main tesi.tex --port 8800 --no-browser
```

L'app gira solo sul tuo computer (`127.0.0.1`): niente viene caricato online.

---

## 3. Progetti

Dalla schermata **Progetti** (pulsante ☰ in alto a sinistra):

- **Progetto LaTeX**: clicca *Scegli la cartella* e seleziona la cartella della tesi nella finestra
  del tuo sistema. Il file principale (quello con `\documentclass`) viene trovato da solo; se ce ne
  sono più di uno (es. `main.tex` e `paper.tex`) scegli quale: ognuno ha revisioni separate.
- **Solo PDF**: trascina il file nel riquadro o cliccalo per sceglierlo.
- I progetti aperti restano in **Recenti**. ✕ li toglie solo dall'elenco, senza cancellare file.

Dove vengono salvate le revisioni:

| Tipo | Cartella |
|---|---|
| LaTeX | `<cartella progetto>/_review/` (aggiungi `_review/` e `build/` al `.gitignore`) |
| PDF importato | `~/.revision2000/pdfs/<id>/_review/` |

Per un progetto LaTeX serve `main.synctex.gz`: se non c'è, premi **▶ Compila** nell'app oppure
compila con `-synctex=1` (Overleaf: scarica il progetto e compila in locale).

---

## 4. Annotare

1. **Seleziona** del testo nel PDF: appare il popup.
2. Premi un **tasto 1–8** per l'azione:

   | Tasto | Azione | Cosa scrivi |
   |---|---|---|
   | 1 | Sostituisci | il nuovo testo (il campo parte già con il testo selezionato) |
   | 2 | Elimina | motivo, opzionale |
   | 3 | Inserisci dopo | il testo da aggiungere |
   | 4 | Riformula | come riformulare, opzionale |
   | 5 | Commento | l'osservazione |
   | 6 | Citazione | quale fonte manca o va corretta |
   | 7 | Verifica | cosa controllare (dato, numero, termine) |
   | 8 | Sposta | nota opzionale; dopo **Invio** selezioni nel PDF il punto di arrivo (il testo va *dopo* quella selezione) |

3. **Invio** salva, **Esc** annulla. Spunta **ovunque** per applicare la correzione a tutte le
   occorrenze (es. un termine da uniformare in tutta la tesi).

Altre scorciatoie: **G** aggiunge una nota generale sulla pagina corrente, **Ctrl+Z** annulla l'ultima
revisione salvata. Cliccando una revisione nella lista vai al punto nel PDF; *Modifica* la riapre per
cambiare testo o azione.

Il simbolo ⚠ indica una revisione non collegata al testo sorgente (formule, tabelle, testo generato
da macro). L'AI userà la riga indicata da SyncTeX.

Nella barra laterale: progetti, nota generale, zoom, ricarica PDF, compila, pagina corrente,
scorciatoie (**?**) e lo slider del tema (chiaro / seppia / scuro, vale anche per il PDF).
Quando riapri un progetto riparti dalla pagina in cui eri rimasto.

---

## 5. Far applicare le revisioni all'AI

1. Premi **Copia prompt AI**.
2. Incollalo in Claude Code (o in un altro agente con accesso ai file) aperto nella cartella del progetto.
   Per un PDF importato, sostituisci `[INDICA QUI IL FILE SORGENTE]` con il documento da modificare.
3. L'AI applica le modifiche e, in `review.json`, segna ogni revisione come `done` o `skipped`
   con una nota (`ai_note`). Tornando sulla pagina vedi le note.
4. **▶ Compila** rigenera il PDF (pdflatex/xelatex + bibtex/biber, file temporanei in `build/`).
   Il PDF si ricarica da solo.

---

## Problemi comuni

| Problema | Soluzione |
|---|---|
| Riavvio mentre l'app è già aperta | nessun problema: viene riaperta la scheda esistente |
| `Porta 8765 occupata da un altro programma` | avvia con `--port 8800` |
| Clic su *Scegli la cartella* e non succede nulla | la finestra può comparire dietro al browser: controlla la barra delle applicazioni, oppure usa *Non vedi la finestra? Sfoglia qui* |
| Revisioni con ⚠ o file sbagliato | il PDF non corrisponde ai sorgenti: ricompila e ricarica (⟳ PDF) |
| `pdflatex non trovato` | installa LaTeX (sezione 1) e riavvia l'app |
| Su Windows, `perl` non trovato | non serve più: l'app non usa `latexmk` |
| Pagina bianca | manca la connessione internet (pdf.js arriva da cdnjs) |
| `./start.sh: Permission denied` | `chmod +x start.sh` |
