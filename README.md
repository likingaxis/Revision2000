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
2. Premi un **tasto 1–9** per l'azione (il riquadro spiega cosa fa ciascuna):

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
   | 9 | Impaginazione | il problema di layout (ci sono scelte rapide: figura fuori posto, esce dal margine, spazio vuoto…) |
   | 0 | Mi piace | perché ti piace, facoltativo. Non è una correzione: l'AI lo usa come esempio del tuo stile |

3. **Invio** salva, **Esc** annulla. Spunta **ovunque** per applicare la correzione a tutte le
   occorrenze (es. un termine da uniformare in tutta la tesi).

**Proponi alternative**: con l'interruttore *Proponi* acceso, l'AI non modifica il testo ma ti propone
3 alternative diverse, ognuna con una breve motivazione. È acceso di default per *Commento* e *Riformula*:
se scrivi solo "questa frase non mi piace", l'AI non decide al posto tuo. Anche con l'interruttore
spento, davanti a indicazioni vaghe l'AI propone invece di applicare. Le proposte compaiono nella scheda
(*da scegliere*): cliccando quella che preferisci, diventa una *Sostituisci* che verrà applicata al
prossimo invio. *Nessuna mi convince* chiede altre alternative, diverse da quelle scartate.

**Mi piace**: i passaggi segnati con *Mi piace* finiscono nella sezione *Stile dell'autore* del
`REVIEW.md`. L'AI li usa come riferimento di tono, ritmo e lessico quando riscrive o propone alternative.

**Problemi di impaginazione** (figure, tabelle, spazi vuoti, cose che escono dal margine): premi
**Area** nella barra (o il tasto **A**, oppure tieni premuto **Alt** e trascina) e disegna un rettangolo
sulla pagina. Si apre l'azione *Impaginazione*. L'area viene collegata al punto del sorgente con SyncTeX
e l'AI riceve istruzioni apposite: sistema il layout senza riscrivere il testo.

**Modifica diretta** (senza AI): premi **Modifica** nella barra (o il tasto **E**), poi clicca una
riga del PDF (viene presa tutta, es. il titolo) o seleziona un pezzo di testo. Si apre il **sorgente
LaTeX** di quel punto: correggilo e premi Invio. Il `.tex` viene salvato subito e la tesi ricompilata.
La sostituzione avviene solo se il testo nel file è ancora identico, le terminazioni di riga restano
quelle del file e ogni modifica resta nello storico (filtro *Tutte*) con **Annulla modifica**; anche
**Ctrl+Z** la annulla. Se il testo non si trova nel sorgente (es. è generato da una macro), puoi creare
una revisione normale per l'AI.

**Scegliere cosa inviare**: ogni revisione aperta ha un cerchio di spunta. Solo quelle spuntate
finiscono nel report, nello ZIP e nel prompt del prossimo invio (*Seleziona tutte* / *Nessuna* in cima
alla lista). Con l'orologio ⏱ **posticipi** una revisione: non viene inviata finché non la riprendi
dal filtro **Dopo** (Aperte · Dopo · Tutte).

Altre scorciatoie: **G** aggiunge una nota generale sulla pagina corrente, **Ctrl+Z** annulla l'ultima
revisione salvata. Cliccando una revisione nella lista vai al punto nel PDF; *Modifica* la riapre per
cambiare testo o azione.

**Pennarello**: per *Elimina*, *Riformula*, *Citazione*, *Verifica* e *Mi piace* c'è l'interruttore
**Fissa**. Accendilo e salva: da quel momento ogni frase che selezioni diventa subito una revisione con
quell'azione, senza riquadro. **Esc** spegne il pennarello.

Sul PDF le revisioni hanno i **segni del correttore**: barrato per *Elimina* e *Sostituisci*, segno di
inserimento per *Inserisci dopo*, sottolineatura ondulata per *Riformula*, puntinata per *Citazione* e
*Verifica*. Accanto alla barra di scorrimento c'è la **mappa**: un trattino colorato per ogni revisione
su tutto il documento; passandoci sopra vedi l'anteprima della pagina, cliccando ci vai.

Nel pannello le revisioni sono **raggruppate per capitolo** (si possono chiudere). Da **Filtri** scegli
ordinamento (pagina, più recenti, priorità), azione e chi le ha segnalate. **Rivedi** (o i tasti **J** e
**K**) le scorre una per una con il PDF che segue, e con *Fatta* o *Dopo* decidi al volo. Le schede si
possono anche **trascinare** su *Fatta*, *Dopo* o *Elimina*; il pannello si allarga trascinandone il bordo.

Il simbolo ⚠ indica una revisione non collegata al testo sorgente (formule, tabelle, testo generato
da macro). L'AI userà la riga indicata da SyncTeX.

Nella barra: progetti, strumenti (Testo, Area, Modifica), nota generale, zoom, ricarica PDF, compila,
pagina corrente, **Guida** (ⓘ, con il *tour guidato* che parte da solo la prima volta che apri un
progetto), scorciatoie (**?**) e lo slider del tema (chiaro / seppia / scuro, vale anche per il PDF).
Con un **doppio clic su un tema** regoli come appare il PDF in quel tema: luminosità del foglio
(o dello sfondo, nello scuro), contrasto del testo e calore. Ogni tema ricorda le sue regolazioni;
*Ripristina* torna ai valori iniziali.
Quando riapri un progetto riparti dalla pagina in cui eri rimasto. La barra si può spostare:
prendila dalla maniglia ⠿ o da un punto vuoto e rilasciala a sinistra, a destra, in alto o in basso.

---

## 5. Far applicare le revisioni all'AI

Premi **Invia all'AI** e scegli una delle due strade. La finestra ti guida passo per passo.

**Agente sul PC** (Claude Code, Cursor, Copilot…), che modifica i file da solo:
1. *Copia prompt*.
2. Incollalo nell'agente aperto nella cartella del progetto. Per un PDF importato, sostituisci
   `[INDICA QUI IL FILE SORGENTE]` con il documento da correggere.
3. L'agente segna ogni revisione come `done` o `skipped` con una nota: tornando sulla pagina le vedi.

**Chat sul web** (ChatGPT, Claude.ai, Gemini…):
1. *Scarica ZIP*: contiene solo i file del documento (i `.tex` inclusi e le immagini/bibliografie
   che usano), le revisioni in `_review/` e il prompt in `PROMPT.txt`.
   Se la chat ha già i file della tesi (es. un progetto di Claude o ChatGPT in cui li hai caricati),
   usa invece **Solo il report (.md)**: scarichi solo le revisioni e il prompt si adatta. Se mancano
   dei file, la chat ti chiederà quali `.tex` incollare.
2. *Copia prompt*, poi nella chat allega lo ZIP (o il report) e incolla il prompt.
3. Metti nella cartella i `.tex` corretti che la chat ti restituisce.

Infine premi **Compila** (pdflatex/xelatex + bibtex/biber, file temporanei in `build/`): il PDF
si ricarica da solo.

### Controllare cosa ha cambiato l'AI

Quando copi il prompt o scarichi lo ZIP, Revision2000 si tiene una copia dei `.tex` di quel momento.
Quando l'AI ha lavorato compare l'avviso **«L'AI ha cambiato N punti · Controlla»**: si apre l'elenco
delle modifiche, capitolo per capitolo, con le parole tolte in rosso e quelle aggiunte in verde e le
revisioni a cui si riferiscono. Per ognuna scegli **Tieni** oppure **Annulla**: *Annulla* rimette nel
file il testo di prima, solo in quel punto, e riapre la revisione collegata. *Tieni tutte* le accetta
in blocco. Dalla scheda di una revisione fatta, *Vedi cosa ha cambiato l'AI* porta dritto alla modifica.
Le correzioni che fai tu (*Modifica diretta*, *Applica al .tex*) non vengono scambiate per modifiche
dell'AI.

Dopo ogni **Compila** (o *Ricarica*) il PDF evidenzia in verde **cosa è cambiato** rispetto alla
versione precedente (in rosso i punti dove è stato tolto del testo). In basso la pillola
*«Il PDF è cambiato in N punti»* ti porta da una modifica all'altra; *Nascondi* toglie i segni.

### Revisione con altre persone

Anche un amico, un relatore o un compagno di corso può rivederti la tesi con Revision2000, senza avere
i file LaTeX. Premi il pulsante con le **due persone**, accanto a *Invia all'AI*.

1. **Tu** scarichi il PDF (*Scarica il PDF*) e glielo mandi.
2. **La persona** installa Revision2000, trascina il PDF in *Solo PDF* e annota come al solito.
   Poi apre la stessa finestra, scrive il suo nome e preme *Esporta le mie note*. Ottiene un file
   `.r2k.json` da mandarti (email, WhatsApp…).
3. **Tu** premi *Importa note* (o trascini il file sulla finestra). Le note entrano tra le tue
   revisioni, con il nome di chi le ha scritte, e vengono collegate da sole ai tuoi `.tex`.
   Se importi due volte lo stesso file non si creano doppioni.

Le correzioni concrete (*Sostituisci*, *Elimina*, *Inserisci*) hanno il pulsante **Applica al .tex**:
vedi il LaTeX già corretto, controlli e premi Invio. Il file viene salvato senza passare dall'AI, e
con Ctrl+Z (o *Annulla modifica*) torni indietro. Se la persona aveva anche i sorgenti e ha usato la
*Modifica diretta*, ricevi la sua modifica LaTeX esatta, pronta da accettare. Le altre note (commenti,
riformulazioni…) le mandi all'AI come sempre.

Conviene che la persona annoti **la stessa versione del PDF** che hai tu: se è diversa, l'app ti avvisa
e ricollega comunque le note in base al testo.

---

## 6. Aggiornare l'app

Se hai scaricato l'app con `git clone`, la schermata **Progetti** controlla da sola se su GitHub ci
sono novità. Se ce ne sono, mostra l'elenco delle modifiche e il pulsante **Aggiorna e riavvia**: l'app
fa `git pull`, si riavvia e la pagina si ricarica. Puoi controllare anche a mano con
*Cerca aggiornamenti*, in fondo alla pagina.

```bash
git clone https://github.com/likingaxis/Revision2000.git
```

Se invece hai scaricato lo ZIP da GitHub, per aggiornare scarica di nuovo la cartella (le revisioni
restano nei tuoi progetti, non nella cartella dell'app).

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
| *Aggiorna e riavvia* dice che hai modifiche locali | hai modificato i file dell'app: `git stash` (o annulla le modifiche) e riprova |
| `./start.sh: Permission denied` | `chmod +x start.sh` |
