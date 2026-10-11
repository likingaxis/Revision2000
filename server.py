"""REVISION2000 - revisione rapida di documenti (progetti LaTeX o PDF qualsiasi).

Uso:  python server.py                       -> schermata progetti nel browser
      python server.py <cartella_latex>      -> apre direttamente quel progetto
Opzioni: --main main.tex  --port 8765  --no-browser
Revisioni: progetto LaTeX -> <cartella>/_review/ ; PDF importati -> ~/.revision2000/pdfs/<id>/_review/
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

__version__ = "1.2.0"
HERE = Path(__file__).resolve().parent
LOCK = threading.Lock()
APP_HOME = Path(os.environ.get("REVISION2000_HOME", Path.home() / ".revision2000"))
REGISTRY = APP_HOME / "projects.json"

ACTIONS = {
    "replace": ("SOSTITUISCI", "Sostituisci il testo ancorato con il nuovo testo indicato."),
    "delete": ("ELIMINA", "Elimina il testo ancorato (sistema punteggiatura/raccordo se serve)."),
    "insert": ("INSERISCI DOPO", "Inserisci il testo indicato subito dopo il testo ancorato."),
    "rewrite": ("RIFORMULA", "Riscrivi il testo ancorato mantenendone il significato, seguendo l'indicazione."),
    "comment": ("COMMENTO", "Osservazione libera: decidi tu l'intervento minimo che la risolve."),
    "cite": ("CITAZIONE", "Serve/va corretta una citazione: usa chiavi esistenti in references.bib; se non esiste una fonte adatta NON inventarla, segnala in ai_note."),
    "check": ("VERIFICA", "Verifica correttezza/coerenza (fatto, numero, termine, riferimento). Modifica solo se l'errore e' certo, altrimenti riporta in ai_note."),
    "move": ("SPOSTA", "Sposta il testo ancorato subito DOPO il testo di destinazione indicato (sistema i raccordi in entrambi i punti)."),
    "general": ("NOTA GENERALE", "Nota non ancorata a un punto preciso: applicala dove pertinente."),
}

# ---------------------------------------------------------------- text matching

TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def clean_pdf_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # sillabazione a fine riga
    return re.sub(r"\s+", " ", s).strip()


def strip_comment(line: str) -> str:
    m = re.search(r"(?<!\\)%", line)
    return line[: m.start()] if m else line


def tex_tokens(lines):
    """[(token_norm, line_idx, start_col, end_col)] ignorando nomi di comandi e commenti."""
    out = []
    for li, raw in enumerate(lines):
        line = strip_comment(raw)
        for m in TOKEN_RE.finditer(line):
            st = m.start()
            if st > 0 and line[st - 1] == "\\":
                continue  # \textbf, \ref, ...
            out.append((norm(m.group()), li, st, m.end()))
    return out


def align(sel, toks, hint_line=None):
    """Allinea i token della selezione a quelli del sorgente. Ritorna (score, i_first, i_last)."""
    if not sel or not toks:
        return (0, None, None)
    best = (0, None, None, 10**9)
    firsts = {}
    for i, t in enumerate(toks):
        firsts.setdefault(t[0], []).append(i)
    starts = set()
    for k in range(min(4, len(sel))):  # parti da uno dei primi token
        for i in firsts.get(sel[k], []):
            starts.add((i, k))
    for i, k in starts:
        matched, first, last, fi, skipped_sel = 1, i, i, i + 1, k
        for s in sel[k + 1:]:
            hit = None
            for d in range(4):  # tollera token di sorgente extra (label, comandi)
                if fi + d < len(toks) and toks[fi + d][0] == s:
                    hit = fi + d
                    break
            if hit is None:
                skipped_sel += 1  # numeri di riferimento, simboli renderizzati...
                if skipped_sel > max(3, len(sel) // 3):
                    break
                continue
            matched += 1
            last = hit
            fi = hit + 1
        dist = abs(toks[first][1] - hint_line) if hint_line is not None else 0
        if matched > best[0] or (matched == best[0] and dist < best[3]):
            best = (matched, first, last, dist)
    return best[:3]


def read_lines_joined(path: Path):
    return "\n".join(read_lines(path))


def read_lines(path: Path):
    try:
        return path.read_text(encoding="utf-8").split("\n")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1").split("\n")


class Project:
    """kind="latex": cartella con sorgenti .tex (ancoraggio SyncTeX + testo, compilazione).
    kind="pdf": PDF importato senza sorgenti (ancoraggio per pagina + testo)."""

    def __init__(self, pid, kind, root: Path, main=None, name=None):
        self.id, self.kind, self.root, self.main = pid, kind, Path(root), main
        self.name = name or self.root.name
        self.pdf = self.root / (Path(main).stem + ".pdf" if kind == "latex" else "document.pdf")
        self.review_dir = self.root / "_review"
        if kind == "latex" and Path(main).stem != "main":  # piu' documenti nella stessa cartella (es. paper.tex)
            self.review_dir = self.review_dir / Path(main).stem
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = self.review_dir / "review.json"
        self.md_path = self.review_dir / "REVIEW.md"
        if not self.json_path.exists():
            self.save({"project": str(self.root), "kind": kind, "main": main, "items": []})

    def info(self):
        n_open = 0
        try:
            n_open = sum(1 for i in self.load()["items"] if i.get("status", "open") == "open")
        except Exception:
            pass
        return {"id": self.id, "kind": self.kind, "name": self.name, "root": str(self.root),
                "main": self.main, "has_pdf": self.pdf.exists(), "open": n_open}

    # ------------------------------------------------------------ storage
    def load(self):
        with open(self.json_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, data):
        tmp = self.json_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.json_path)
        self.write_md(data)

    def rel(self, p: Path) -> str:
        try:
            return p.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    # ------------------------------------------------------------ locate
    def synctex(self, page, x, y):
        try:
            r = subprocess.run(
                ["synctex", "edit", "-o", f"{page}:{x:.1f}:{y:.1f}:{self.pdf.name}"],
                cwd=self.root, capture_output=True, text=True, timeout=10,
            )
        except Exception:
            return None, None
        f = re.search(r"^Input:(.+)$", r.stdout, re.M)
        l = re.search(r"^Line:(\d+)$", r.stdout, re.M)
        if not f or not l:
            return None, None
        return Path(f.group(1).strip()), int(l.group(1))

    def tex_files(self):
        """File .tex che fanno parte del documento: quelli elencati da SyncTeX (cosi' un paper.tex
        nella stessa cartella non viene confuso con la tesi); altrimenti tutti i .tex del progetto."""
        sync = self.root / (Path(self.main).stem + ".synctex.gz") if self.main else None
        if sync and sync.exists():
            import gzip
            files = []
            try:
                with gzip.open(sync, "rt", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("Input:"):
                            fp = Path(line.split(":", 2)[2].strip())
                            if fp.suffix == ".tex" and fp.exists() and self.root in fp.resolve().parents:
                                files.append(fp.resolve())
            except OSError:
                files = []
            if files:
                return list(dict.fromkeys(files))
        skip = {"_review", "build", "_cestino", ".git"}
        return [p for p in self.root.rglob("*.tex") if not skip & set(p.parts)]

    def locate(self, page, x, y, text):
        if self.kind == "pdf":  # nessun sorgente: basta pagina + testo selezionato
            return {"file": None, "line": None, "source_match": None, "confidence": None, "synctex": None}
        sfile, sline = self.synctex(page, x, y) if page else (None, None)
        sel = [norm(t) for t in TOKEN_RE.findall(clean_pdf_text(text or ""))]
        res = {"file": None, "line": None, "line_end": None, "source_match": None,
               "source_context": None, "confidence": 0.0, "synctex": None}
        if sfile:
            res["synctex"] = f"{self.rel(sfile)}:{sline}"
            res["file"], res["line"], res["line_end"] = self.rel(sfile), sline, sline

        candidates = []
        if sfile and sfile.exists():
            candidates.append((sfile, sline - 1))
        if sel:
            def score_of(path, hint):
                lines = read_lines(path)
                toks = tex_tokens(lines)
                sc, a, b = align(sel, toks, hint)
                return sc, a, b, lines, toks
            best = None
            for path, hint in candidates:
                r = score_of(path, hint)
                best = (path,) + r
            if best is None or best[1] < 0.6 * len(sel):
                for path in self.tex_files():
                    if sfile and path.resolve() == sfile.resolve():
                        continue
                    r = score_of(path, None)
                    if best is None or r[0] > best[1]:
                        best = (path,) + r
            if best and best[2] is not None and best[1] >= max(1, 0.5 * len(sel)):
                path, sc, a, b, lines, toks = best
                la, ca = toks[a][1], toks[a][2]
                lb, cb = toks[b][1], toks[b][3]
                # estendi alla punteggiatura finale immediatamente adiacente
                m = re.match(r"[.,;:!?)\]}]*", lines[lb][cb:])
                cb += len(m.group()) if m else 0
                if la == lb:
                    match = lines[la][ca:cb]
                else:
                    match = "\n".join([lines[la][ca:]] + lines[la + 1:lb] + [lines[lb][:cb]])
                res.update(file=self.rel(path), line=la + 1, line_end=lb + 1, col=ca + 1,
                           source_match=match, confidence=round(sc / len(sel), 2))
        if res["file"] and res["line"]:
            p = self.root / res["file"]
            if p.exists():
                lines = read_lines(p)
                a, b = max(0, res["line"] - 1), min(len(lines), (res["line_end"] or res["line"]))
                ctx = "\n".join(lines[a:b])
                res["source_context"] = ctx if len(ctx) < 4000 else ctx[:4000] + " [...]"
        return res

    # ------------------------------------------------------------ compile
    def compile(self):
        """pdf/xe/lualatex + bibtex/biber senza latexmk (non serve Perl), Windows (MiKTeX) e
        Linux/macOS (TeX Live). File ausiliari in build/, nella cartella restano PDF e .synctex.gz."""
        if self.kind != "latex":
            return {"ok": False, "errors": ["Un PDF importato non si compila."], "tail": ""}
        src = (self.root / self.main).read_text(encoding="utf-8", errors="replace")
        engine = "xelatex" if re.search(r"\\usepackage(\[[^]]*\])?\{(fontspec|unicode-math)\}", src) else "pdflatex"
        if not shutil.which(engine):
            return {"ok": False, "errors": [f"{engine} non trovato: installa MiKTeX (Windows) o TeX Live (Linux/macOS), vedi README."], "tail": ""}
        build = self.root / "build"
        build.mkdir(exist_ok=True)
        for f in self.tex_files():  # \include di file in sottocartelle richiede le stesse sottocartelle in build/
            rel = f.parent.relative_to(self.root)
            if str(rel) != ".":
                (build / rel).mkdir(parents=True, exist_ok=True)
        stem = Path(self.main).stem
        run = lambda cmd, cwd, env=None: subprocess.run(
            cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
        miktex = "MiKTeX" in run([engine, "--version"], self.root).stdout
        # MiKTeX: -aux-directory lascia il PDF nella cartella; TeX Live: -output-directory e poi lo spostiamo
        tex = [engine, "-synctex=1", "-interaction=nonstopmode", "-file-line-error",
               "-aux-directory=build" if miktex else "-output-directory=build", self.main]

        def latex():
            r = run(tex, self.root)
            if not miktex:
                for ext in (".pdf", ".synctex.gz"):
                    if (build / (stem + ext)).exists():
                        os.replace(build / (stem + ext), self.root / (stem + ext))
            return r.stdout

        out = latex()
        env = dict(os.environ, BIBINPUTS=f"{self.root}{os.pathsep}", BSTINPUTS=f"{self.root}{os.pathsep}")
        if (build / f"{stem}.bcf").exists() and shutil.which("biber"):
            out += run(["biber", "--input-directory", str(self.root), stem], build, env).stdout
        elif "\\bibdata" in "".join(f.read_text(encoding="utf-8", errors="replace") for f in build.rglob("*.aux")):
            out += run(["bibtex", stem], build, env).stdout
        for _ in range(2):
            out = latex()
            if "Rerun to get" not in out and "undefined references" not in out and "Please rerun" not in out:
                break
        errs = [l for l in out.splitlines() if re.search(r"\.tex:\d+:|^! ", l)]
        ok = (self.root / f"{stem}.pdf").exists() and not errs
        return {"ok": ok, "errors": errs[:30], "tail": out[-3000:]}

    # ------------------------------------------------------------ consegna all'AI
    def prompt(self, mode="agent"):
        """agent: agente con accesso ai file (Claude Code, Cursor...); chat: chat web a cui si carica lo ZIP."""
        if mode == "chat":
            if self.kind == "latex":
                return ("Ti allego uno ZIP con il mio progetto LaTeX (file principale: " + self.main + ") e la cartella _review/. "
                        "In _review/REVIEW.md trovi le revisioni da applicare, con le istruzioni: seguile esattamente, "
                        "facendo solo le modifiche richieste e senza toccare il resto. "
                        "Alla fine restituiscimi, come file scaricabili, SOLO i file .tex che hai modificato, completi e pronti da sostituire "
                        "(se possibile in un unico ZIP con la stessa struttura di cartelle), piu' _review/review.json aggiornato "
                        "con status (\"done\" o \"skipped\") e ai_note per ogni revisione. "
                        "Poi elencami in breve le revisioni saltate o dubbie.")
            return ("Ti allego uno ZIP con il PDF \"" + self.name + "\" e _review/REVIEW.md, che contiene le revisioni annotate sul PDF "
                    "(pagina + testo). Per ogni revisione restituiscimi il testo corretto, nell'ordine e con l'id (R001, R002...), "
                    "seguendo le istruzioni di REVIEW.md; se allego anche il file sorgente (Word, LaTeX, Markdown...) applicale direttamente "
                    "e restituiscimi il file modificato.")
        if self.kind == "latex":
            return (f"Leggi `{self.md_path}` e applica ai file .tex di `{self.root}` tutte le revisioni aperte, "
                    f"seguendo esattamente le istruzioni del file. Aggiorna status e ai_note in `{self.json_path}` per ogni item.")
        return (f"Leggi `{self.md_path}`: contiene revisioni annotate sul PDF \"{self.name}\". Applicale al documento sorgente "
                f"[INDICA QUI IL FILE SORGENTE], seguendo le istruzioni del file. Aggiorna status e ai_note in `{self.json_path}` per ogni item.")

    SRC_EXT = {".tex", ".bib", ".cls", ".sty", ".bst", ".bbx", ".cbx", ".def", ".cfg", ".clo",
               ".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".tikz", ".csv", ".dat", ".txt"}
    SKIP_DIRS = {"build", "_review", "_cestino", ".git", "node_modules", "__pycache__", ".claude"}

    def export_zip(self):
        """ZIP da caricare in una chat web: sorgenti del progetto + _review/ + PROMPT.txt."""
        import io, zipfile
        buf = io.BytesIO()
        stem = Path(self.main).stem if self.main else ""
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            if self.kind == "latex":
                # solo i .tex del documento + i file che citano (immagini, .bib, classi locali):
                # un paper.tex o altri materiali nella stessa cartella non finiscono nello ZIP
                texs = self.tex_files()
                text = "\n".join(read_lines_joined(t) for t in texs)
                for t in texs:
                    z.write(t, t.relative_to(self.root).as_posix())
                for f in sorted(self.root.rglob("*")):
                    rel = f.relative_to(self.root)
                    if (not f.is_file() or f.suffix.lower() == ".tex" or self.SKIP_DIRS & set(rel.parts)
                            or f.suffix.lower() not in self.SRC_EXT or f.stat().st_size > 15_000_000
                            or rel.as_posix() == f"{stem}.pdf"):
                        continue
                    noext = rel.with_suffix("").as_posix()
                    used = (noext in text or rel.as_posix() in text
                            or (f.parent == self.root and f.suffix.lower() in {".cls", ".sty", ".bst"}))
                    if used:
                        z.write(f, rel.as_posix())
            else:
                z.write(self.pdf, f"{self.name}.pdf")
            z.write(self.md_path, "_review/REVIEW.md")
            z.write(self.json_path, "_review/review.json")
            z.writestr("PROMPT.txt", self.prompt("chat"))
        safe = re.sub(r"[^\w.-]+", "_", self.name).strip("_") or "progetto"
        return buf.getvalue(), f"{safe}_per_AI.zip"

    # ------------------------------------------------------------ markdown export
    def write_md(self, data):
        items = data.get("items", [])
        open_items = [i for i in items if i.get("status", "open") == "open"]
        y0 = lambda i: (i.get("rects") or [{}])[0].get("y", 0)
        open_items.sort(key=lambda i: (i.get("file") or "~", i.get("line") or 0, i.get("col") or 0, i.get("page") or 0, y0(i)))
        L = []
        L.append("# Revisione documento - istruzioni per l'AI\n")
        if self.kind == "latex":
            L.append(f"Progetto: `{self.root}`  ·  file principale: `{self.main}`  ·  generato: {datetime.now():%Y-%m-%d %H:%M}\n")
        else:
            L.append(f"Documento PDF: **{self.name}** (`{self.pdf}`)  ·  generato: {datetime.now():%Y-%m-%d %H:%M}\n")
            L.append("> Questo PDF NON e' collegato a sorgenti: le revisioni sono ancorate a **pagina + testo nel PDF**. "
                     "Applicale al documento sorgente indicato dall'utente (LaTeX, Word, Markdown...) cercando il `Testo nel PDF`; "
                     "se il sorgente non e' disponibile, restituisci il testo corretto di ogni revisione.\n")
        L.append(f"Revisioni aperte: **{len(open_items)}** (totali: {len(items)}). Dati completi in `_review/review.json`.\n")
        L.append("""## Come procedere

1. Per ogni revisione qui sotto, apri il file `.tex` indicato e localizza il punto usando **`Sorgente ancorato`** come stringa esatta (old_string). Il numero di riga e' indicativo: se il file e' cambiato, cerca per testo. Se manca il sorgente ancorato, usa `Testo nel PDF` e la riga SyncTeX.
2. Applica l'**azione** richiesta (vedi legenda) con la modifica *minima* necessaria. Preserva comandi LaTeX, `\\ref`, `\\cite`, `\\label`, ambienti e formattazione. Mantieni lo stile accademico italiano della tesi.
3. Dopo ogni revisione aggiorna l'item corrispondente (stesso `id`) in `review.json` (stessa cartella di questo file): `"status": "done"` (oppure `"skipped"` se non applicabile/ambigua) e `"ai_note"`: breve descrizione di cosa hai fatto o del dubbio. Non modificare gli altri campi.
4. Se un'indicazione e' ambigua o richiede contenuti che non conosci (dati, fonti), NON inventare: `skipped` + spiegazione in `ai_note`.
5. Alla fine riassumi in chat le revisioni saltate o dubbie. Non ricompilare a meno che non sia richiesto.

### Legenda azioni
""")
        for k, (lab, desc) in ACTIONS.items():
            L.append(f"- **{lab}** (`{k}`): {desc}")
        L.append("")
        cur = object()
        for it in open_items:
            if it.get("file") != cur:
                cur = it.get("file")
                L.append(f"\n## `{cur}`\n" if cur else ("\n## Revisioni per pagina\n" if self.kind == "pdf" else "\n## Senza file associato\n"))
            lab = ACTIONS.get(it["action"], (it["action"].upper(),))[0]
            prio = f" · priorita' {it['priority']}" if it.get("priority") and it["priority"] != "normale" else ""
            if it.get("line"):
                L.append(f"### {it['id']} · {lab} · `{it.get('file')}:{it.get('line')}` · pag. PDF {it.get('page') or '-'}{prio}\n")
            else:
                L.append(f"### {it['id']} · {lab} · pag. PDF {it.get('page') or '-'}{prio}\n")
            if it.get("pdf_text"):
                L.append(f"- **Testo nel PDF:** «{it['pdf_text']}»")
            if it.get("source_match"):
                L.append(f"- **Sorgente ancorato** (confidenza {it.get('confidence')}):\n\n```latex\n{it['source_match']}\n```")
            elif it.get("source_context"):
                L.append(f"- **Contesto sorgente (riga SyncTeX, ancoraggio testuale fallito):**\n\n```latex\n{it['source_context']}\n```")
            dest = it.get("dest")
            if dest:
                dloc = f"{dest.get('file')}:{dest.get('line')}" if dest.get("line") else "posizione non determinata"
                L.append(f"- **Destinazione** (`{dloc}`, pag. PDF {dest.get('page')}): sposta DOPO «{dest.get('pdf_text')}»")
                if dest.get("source_match"):
                    L.append(f"\n```latex\n{dest['source_match']}\n```")
            elif it["action"] == "move":
                L.append("- **Destinazione:** non indicata: usa l'indicazione, altrimenti `skipped`.")
            if it.get("scope") == "all":
                L.append("- **Ambito: TUTTE le occorrenze** di questo testo/termine nei file `.tex` della tesi (cerca con grep; applica solo dove il senso e' lo stesso e riporta in ai_note quante modifiche e in quali file).")
            note = (it.get("note") or "").strip()
            if note:
                head = {"replace": "Nuovo testo", "insert": "Testo da inserire", "move": "Destinazione"}.get(it["action"], "Indicazione")
                L.append(f"- **{head}:**\n\n```\n{note}\n```")
            L.append("")
        self.md_path.write_text("\n".join(L), encoding="utf-8")


# -------------------------------------------------------------------- registro progetti

PROJECTS = {}


def load_registry():
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_registry(reg):
    APP_HOME.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_project(pid):
    if pid in PROJECTS:
        return PROJECTS[pid]
    for e in load_registry():
        if e["id"] == pid and Path(e["root"]).exists():
            PROJECTS[pid] = Project(e["id"], e["kind"], Path(e["root"]), e.get("main"), e.get("name"))
            return PROJECTS[pid]
    return None


def register(entry):
    reg = [e for e in load_registry() if e["id"] != entry["id"]]
    entry["opened"] = datetime.now().isoformat(timespec="seconds")
    save_registry([entry] + reg)
    PROJECTS.pop(entry["id"], None)
    return get_project(entry["id"])


def main_candidates(root: Path):
    c = [f.name for f in sorted(root.glob("*.tex"))
         if re.search(r"^\s*\\documentclass", f.read_text(encoding="utf-8", errors="replace"), re.M)]
    return sorted(c, key=lambda n: (n != "main.tex", n))


def add_latex(path, main=None):
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Cartella non trovata: {root}")
    cands = main_candidates(root)
    if not cands:
        raise ValueError("Nessun file .tex con \\documentclass nella cartella (scegli la cartella principale del progetto).")
    main = main if main in cands else cands[0]
    pid = "tex-" + hashlib.sha1(f"{str(root).lower()}|{main}".encode()).hexdigest()[:10]
    return register({"id": pid, "kind": "latex", "root": str(root), "main": main, "name": root.name})


def add_pdf(filename, data: bytes):
    if not data.startswith(b"%PDF"):
        raise ValueError("Il file non sembra un PDF.")
    pid = "pdf-" + hashlib.sha1(data).hexdigest()[:10]
    root = APP_HOME / "pdfs" / pid
    root.mkdir(parents=True, exist_ok=True)
    (root / "document.pdf").write_bytes(data)
    return register({"id": pid, "kind": "pdf", "root": str(root), "name": Path(filename).stem or "documento"})


def browse(path):
    """Mini esploratore di cartelle per scegliere un progetto LaTeX dal browser."""
    if not path:
        path = str(Path.home())
    p = Path(path).expanduser()
    if os.name == "nt" and path in ("\\", "/", "drives"):
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{d}:\\").exists()]
        return {"path": "", "parent": None, "dirs": [{"name": d, "path": d} for d in drives], "tex": []}
    p = p.resolve()
    dirs, tex = [], []
    try:
        for c in sorted(p.iterdir(), key=lambda c: c.name.lower()):
            if c.name.startswith((".", "$")):
                continue
            if c.is_dir():
                dirs.append({"name": c.name, "path": str(c)})
            elif c.suffix == ".tex":
                tex.append(c.name)
    except PermissionError:
        pass
    parent = str(p.parent) if p.parent != p else ("drives" if os.name == "nt" else None)
    return {"path": str(p), "parent": parent, "dirs": dirs[:400], "tex": tex, "main": main_candidates(p) if tex else []}


PICK_TK = r"""
import sys, tkinter as tk
from tkinter import filedialog
# finestra "proprietaria" invisibile e sempre in primo piano: il dialogo eredita il topmost
r = tk.Tk(); r.overrideredirect(True); r.attributes("-alpha", 0.0); r.attributes("-topmost", True)
r.geometry("1x1+%d+%d" % (r.winfo_screenwidth() // 2 - 300, r.winfo_screenheight() // 2 - 250))
r.update(); r.lift(); r.focus_force()
if sys.platform == "win32":  # Windows blocca il primo piano ai processi in background: piccolo trucco con ALT
    try:
        import ctypes
        u = ctypes.windll.user32
        u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x12, 0, 2, 0)
        u.SetForegroundWindow(int(r.wm_frame(), 16))
    except Exception:
        pass
p = filedialog.askdirectory(parent=r, title="Scegli la cartella del progetto LaTeX", mustexist=True)
sys.stdout.write(p or "")
"""


def pick_folder():
    """Finestra nativa di selezione cartella (gira sul PC dell'utente, il server e' locale)."""
    title = "Scegli la cartella del progetto LaTeX"
    attempts = [[sys.executable, "-c", PICK_TK]]
    if sys.platform == "darwin":
        attempts.append(["osascript", "-e", f'POSIX path of (choose folder with prompt "{title}")'])
    elif os.name != "nt":
        attempts += [["zenity", "--file-selection", "--directory", f"--title={title}"],
                     ["kdialog", "--getexistingdirectory", str(Path.home()), "--title", title]]
    for cmd in attempts:
        if cmd[0] != sys.executable and not shutil.which(cmd[0]):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        except Exception:
            continue
        if cmd[0] == sys.executable and "Error" in r.stderr and not r.stdout.strip():
            continue  # tkinter non disponibile: prova il prossimo
        path = r.stdout.strip()
        if not path:
            return {"cancelled": True}
        root = Path(path)
        return {"path": str(root), "main": main_candidates(root) if root.is_dir() else []}
    return {"unavailable": True}


def tools_status():
    return {t: bool(shutil.which(t)) for t in ("pdflatex", "synctex", "bibtex", "biber", "xelatex")}


def install_hint():
    """Comando per installare LaTeX sul sistema corrente (mostrato nella home se manca)."""
    if os.name == "nt":
        return "winget install --id MiKTeX.MiKTeX -e"
    if sys.platform == "darwin":
        return "brew install --cask mactex-no-gui"
    for pm, cmd in (("apt", "sudo apt install -y texlive-latex-extra texlive-lang-italian texlive-bibtex-extra biber python3-tk"),
                    ("dnf", "sudo dnf install -y texlive-scheme-medium biber python3-tkinter"),
                    ("pacman", "sudo pacman -S --needed texlive-basic texlive-latexextra texlive-langitalian texlive-bibtexextra biber tk"),
                    ("zypper", "sudo zypper install -y texlive-scheme-medium biber python3-tk")):
        if shutil.which(pm):
            return cmd
    return "./install.sh"


# -------------------------------------------------------------------- HTTP

def make_handler():
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, ctype="application/json"):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def raw(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n)

        def body(self):
            return json.loads(self.raw() or b"{}")

        def proj(self):
            q = parse_qs(urlparse(self.path).query)
            return get_project((q.get("p") or [""])[0])

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/projects":
                ps = [get_project(e["id"]) for e in load_registry()]
                return self.send(200, {"projects": [p.info() for p in ps if p], "tools": tools_status(), "home": str(Path.home()),
                                       "install": install_hint(), "version": __version__})
            if u.path == "/api/browse":
                return self.send(200, browse((q.get("path") or [""])[0]))
            proj = self.proj()
            if proj is None:
                return self.send(404, {"error": "progetto non trovato"})
            if u.path == "/pdf":
                if not proj.pdf.exists():
                    return self.send(404, {"error": "PDF non trovato"})
                return self.send(200, proj.pdf.read_bytes(), "application/pdf")
            if u.path == "/api/items":
                with LOCK:
                    d = proj.load()
                d["pdf_mtime"] = proj.pdf.stat().st_mtime if proj.pdf.exists() else 0
                d["actions"] = {k: v[0] for k, v in ACTIONS.items()}
                d["info"] = proj.info()
                return self.send(200, d)
            if u.path == "/api/prompt":
                return self.send(200, {"prompt": proj.prompt((q.get("mode") or ["agent"])[0])})
            if u.path == "/api/export.zip":
                data, fname = proj.export_zip()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                return self.wfile.write(data)
            self.send(404, {"error": "not found"})

        def do_POST(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/api/pick-folder":
                return self.send(200, pick_folder())
            try:
                if u.path == "/api/projects/latex":
                    b = self.body()
                    return self.send(200, add_latex(b.get("path", ""), b.get("main")).info())
                if u.path == "/api/projects/pdf":
                    return self.send(200, add_pdf((q.get("name") or ["documento.pdf"])[0], self.raw()).info())
            except ValueError as e:
                return self.send(400, {"error": str(e)})
            proj = self.proj()
            if proj is None:
                return self.send(404, {"error": "progetto non trovato"})
            if u.path == "/api/locate":
                b = self.body()
                return self.send(200, proj.locate(b.get("page"), b.get("x", 0), b.get("y", 0), b.get("text", "")))
            if u.path == "/api/items":
                b = self.body()
                with LOCK:
                    d = proj.load()
                    n = max([int(re.sub(r"\D", "", i["id"]) or 0) for i in d["items"]] + [0]) + 1
                    b["id"] = f"R{n:03d}"
                    b.setdefault("status", "open")
                    b["created"] = datetime.now().isoformat(timespec="seconds")
                    d["items"].append(b)
                    proj.save(d)
                return self.send(200, b)
            if u.path == "/api/compile":
                try:
                    return self.send(200, proj.compile())
                except Exception as e:
                    return self.send(200, {"ok": False, "errors": [str(e)], "tail": ""})
            self.send(404, {"error": "not found"})

        def do_PATCH(self):
            proj = self.proj()
            iid = urlparse(self.path).path.rsplit("/", 1)[-1]
            b = self.body()
            with LOCK:
                d = proj.load()
                for it in d["items"]:
                    if it["id"] == iid:
                        it.update(b)
                        proj.save(d)
                        return self.send(200, it)
            self.send(404, {"error": "not found"})

        def do_DELETE(self):
            u = urlparse(self.path)
            iid = u.path.rsplit("/", 1)[-1]
            if u.path.startswith("/api/projects/"):  # rimuove solo dall'elenco, non cancella file
                save_registry([e for e in load_registry() if e["id"] != iid])
                PROJECTS.pop(iid, None)
                return self.send(200, {"ok": True})
            proj = self.proj()
            with LOCK:
                d = proj.load()
                d["items"] = [i for i in d["items"] if i["id"] != iid]
                proj.save(d)
            self.send(200, {"ok": True})

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default=None)
    ap.add_argument("--main", default="main.tex")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--version", action="version", version=f"Revision2000 {__version__}")
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.port}/"
    if a.project:
        try:
            proj = add_latex(a.project, a.main)
        except ValueError as e:
            sys.exit(str(e))
        proj.write_md(proj.load())
        url += f"?p={proj.id}"
        print(f"Progetto: {proj.root} ({proj.main})  ·  revisioni in {proj.review_dir}")
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler())
    except OSError:
        # probabilmente l'app e' gia' aperta (doppio avvio): basta riaprire il browser
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{a.port}/api/projects", timeout=2)
            print(f"Revision2000 e' gia' in esecuzione: apro {url}")
            if not a.no_browser:
                webbrowser.open(url)
            return
        except Exception:
            sys.exit(f"Porta {a.port} occupata da un altro programma. Usa --port per sceglierne un'altra.")
    print(f"REVISION2000 attivo su {url}\nCtrl+C per uscire")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
