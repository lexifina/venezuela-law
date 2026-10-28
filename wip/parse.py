"""Parse the cached official texts into corpus.json (gitlaw_common/SCHEMA.md).

Reads only .cache/ (no network). PDFs are turned into text with poppler's
`pdftotext -enc UTF-8 -layout` (deterministic for a given poppler version; the
version is recorded in corpus.json decisions).

    python -X utf8 parse.py            write corpus.json (atomically via corpus.json.tmp)
    python -X utf8 parse.py --verify   also print the cross-checks against the independent transcriptions
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
OUT = HERE / "corpus.json"
DOCS_DATE = "2026-10-28"

# Pinned sources (URL -> cache by sha256 of the URL).
SRC_5908 = "https://ine.gob.ve/wp-content/uploads/2024/08/1-ConstitucionVzla_GacetaOficial_5908.pdf"
SRC_TSJ_HTML = "https://web.archive.org/web/20141025044650id_/http://www.tsj.gob.ve/legislacion/constitucion1999.htm"
SRC_AN_1999 = "https://www.asambleanacional.gob.ve/storage/documentos/botones/constitucion-nacional-20191205135853.PDF"
SRC_TSJ_CONST_PAGE = "https://www.tsj.gob.ve/constitucion"

ORDINALS = ["Primera", "Segunda", "Tercera", "Cuarta", "Quinta", "Sexta", "Séptima", "Octava", "Novena",
            "Décima", "Decimoprimera", "Decimosegunda", "Decimotercera", "Decimocuarta", "Decimoquinta",
            "Decimosexta", "Decimoséptima", "Decimoctava", "Decimonovena", "Vigésima"]


def cache_path(url: str) -> Path:
    return CACHE / hashlib.sha256(url.encode("utf-8")).hexdigest()


def sha_of(url: str) -> str:
    return hashlib.sha256(cache_path(url).read_bytes()).hexdigest()


def pdftotext(url: str) -> str:
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(cache_path(url)), "-"],
                       capture_output=True, check=True)
    return r.stdout.decode("utf-8")


def pdftotext_version() -> str:
    r = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True)
    return ((r.stderr or r.stdout).splitlines() or ["?"])[0].strip()


def norm(s: str) -> str:
    """Normalise publisher typesetting once: NBSP, quotes, dashes, spaces."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ").replace("­", "")
    s = s.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"')
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


# ---------------------------------------------------------------- layout text -> logical lines

ITEM_RE = re.compile(r"^(\d{1,2}|[a-zñ])[\.\)]\s+\S")
ART_RE = re.compile(r"^Artículo (\d+)\.\s*(.*)$")
ORD_RE = re.compile(r"^(" + "|".join(ORDINALS) + r"|Única)\.\s*(.*)$")


def layout_lines(text: str) -> list[tuple[int, str]]:
    """(indent, text) for every line, page numbers removed; '' marks a blank line."""
    out: list[tuple[int, str]] = []
    for page in text.split("\f"):
        lines = page.split("\n")
        for ln in lines:
            if re.fullmatch(r"\s*\d{1,3}\s*", ln):
                continue  # page number
            if not ln.strip():
                out.append((0, ""))
                continue
            ind = len(ln) - len(ln.lstrip(" "))
            out.append((ind, ln.rstrip()))
    return out


HEAD_RE = re.compile(r"^(TÍTULO [IVXL]+|T[íi]tulo [IVXL]+|CAP[ÍI]TULO [IVXL]+|Cap[íi]tulo [IVXL]+|Secci[óo]n \w+:)", re.I)
DISP_HEAD_RE = re.compile(r"^(Disposici[óo]n|Disposiciones) (Final|Derogatoria|Transitorias)$", re.I)


def is_heading(ind: int, s: str, prev_heading: bool = False) -> bool:
    t = s.strip()
    if ITEM_RE.match(t) or ART_RE.match(t):
        return False
    if ind >= 12:
        return True
    if HEAD_RE.match(t) or DISP_HEAD_RE.match(t):
        return True
    # the name line under 'TÍTULO II' / 'Capítulo II', indented less than a centred line
    return prev_heading and ind >= 4 and (t.upper() == t or t.startswith(("De ", "Del ")))


def paragraphs(lines: list[tuple[int, str]]) -> list[tuple[str, str]]:
    """Join wrapped lines into paragraphs. Returns [(kind, text)], kind 'h' heading or 'p' paragraph."""
    out: list[tuple[str, str]] = []
    cur: list[str] = []
    pending_blank = False

    def flush():
        nonlocal cur
        if cur:
            out.append(("p", norm(" ".join(cur))))
            cur = []

    for ind, s in lines:
        if s == "":
            pending_blank = True
            continue
        t = s.strip()
        if is_heading(ind, s, bool(out) and out[-1][0] == "h" and not cur):
            flush()
            out.append(("h", norm(t)))
            pending_blank = False
            continue
        starts_new = bool(ART_RE.match(t) or ORD_RE.match(t) or ITEM_RE.match(t) or t.startswith("(Ver Enmienda"))
        if cur and not starts_new:
            prev = cur[-1]
            ends = prev.rstrip()[-1:] in ".:;)"
            if pending_blank and ends and not t[:1].islower():
                flush()
        else:
            flush()
        cur.append(t)
        pending_blank = False
    flush()
    # a wrapped line that starts lowercase after a list item: already joined above
    return out


# ---------------------------------------------------------------- Constitution 1999 (G.O. 5.908 reprint)

def parse_5908() -> tuple[dict, dict, list[str]]:
    """Return (units_1999, enmienda_units, notes) from the G.O. 5.908 text."""
    text = pdftotext(SRC_5908)
    i_pre = text.index("PREÁMBULO")
    i_enm = text.index("ENMIENDA N° 1 DE LA CONSTITUCIÓN")
    body = text[text.rindex("\n", 0, i_pre) + 1:text.rindex("EL PRESIDENTE,", 0, i_enm)]
    paras = paragraphs(layout_lines(body))
    units: dict[str, dict] = {}
    titulos: list[str] = []
    key = None
    section = "pre"
    heading_buf: list[str] = []

    def add(k, label, kind, line):
        units.setdefault(k, {"label": label, "kind": kind, "lines": []})["lines"].append(line)

    for kind, t in paras:
        if kind == "h":
            if t == "PREÁMBULO":
                key = "preambulo"
                continue
            if t == "CONSTITUCIÓN" and section == "pre":
                add("preambulo", "Preámbulo", "preamble", t)
                continue
            if t.startswith("DISPOSICIÓN DEROGATORIA"):
                section = "derog"
            elif t.startswith("DISPOSICIONES TRANSITORIAS"):
                section = "trans"
            elif t.startswith("DISPOSICIÓN FINAL"):
                section = "final"
            titulos.append(t)
            continue
        m = ART_RE.match(t)
        o = ORD_RE.match(t)
        if m:
            section = "art"
            n = int(m.group(1))
            key = f"art-{n:03d}"
            if key in units:
                raise SystemExit(f"duplicate {key}")
            add(key, f"Art. {n}", "art", t)
        elif o and section in ("derog", "trans", "final"):
            word = o.group(1)
            if section == "trans":
                n = ORDINALS.index(word) + 1
                key = f"disp-transitoria-{n:02d}"
                add(key, f"Disposición transitoria {word.lower()}", "transitional", t)
            elif section == "derog":
                key = "disp-derogatoria"
                add(key, "Disposición derogatoria única", "repeal", t)
            else:
                key = "disp-final"
                add(key, "Disposición final única", "final", t)
        elif t.startswith("(Ver Enmienda"):
            units[key].setdefault("ver_enmienda", True)
        elif t.startswith("Aprobada por el pueblo de Venezuela"):
            key = "promulgacion"
            add(key, "Aprobación y proclamación", "closing", t)
        else:
            if key is None:
                raise SystemExit(f"text before first unit: {t[:60]}")
            if key == "preambulo" and section == "pre":
                add(key, "Preámbulo", "preamble", t)
            else:
                units[key]["lines"].append(t)
    # headings: keep in order, grouping 'TÍTULO I' + its name, 'Capítulo I' + its name
    units["titulos"] = {"label": "Títulos, capítulos y secciones", "kind": "heading", "lines": group_headings(titulos)}

    # Enmienda N° 1 text (pp. 105-107)
    enm = text[i_enm:]
    e_paras = paragraphs(layout_lines(enm))
    e_units: dict[str, list[str]] = {}
    ek = None
    in_art1 = False
    for kind, t in e_paras:
        if kind == "h":
            continue
        if t.startswith("Artículo 1. Se enmienda"):
            in_art1 = True
            continue
        if t.startswith("Artículo 2. Imprímase"):
            break
        m = ART_RE.match(t)
        if in_art1 and m:
            ek = f"art-{int(m.group(1)):03d}"
            e_units[ek] = [t]
        elif ek:
            e_units[ek].append(t)
    ver = sorted(k for k, u in units.items() if u.get("ver_enmienda"))
    return units, e_units, ver


def group_headings(hs: list[str]) -> list[str]:
    out: list[str] = []
    for h in hs:
        if out and not (HEAD_RE.match(h) or DISP_HEAD_RE.match(h) or h.startswith("DISPOSICI")):
            if re.fullmatch(r"(TÍTULO|Capítulo|CAPÍTULO) [IVXL]+", out[-1]):
                out[-1] = out[-1] + ". " + h  # 'TÍTULO I' + its name
            else:
                out[-1] = out[-1] + " " + h  # a heading wrapped onto a second line
        else:
            out.append(h)
    return out


def finish(units: dict) -> dict:
    res = {}
    for k in sorted(units, key=sort_key):
        u = units[k]
        res[k] = {"label": u["label"], "kind": u["kind"], "text": "\n".join(u["lines"]) + "\n"}
    return res


def sort_key(k: str):
    order = {"preambulo": 0, "titulos": 9}
    if k in order:
        return (order[k], 0, k)
    if k.startswith("art-"):
        return (1, int(k[4:7]), k)
    if k == "disp-derogatoria":
        return (2, 0, k)
    if k.startswith("disp-transitoria"):
        return (3, int(k.rsplit("-", 1)[1]), k)
    if k == "disp-final":
        return (4, 0, k)
    return (5, 0, k)


# ---------------------------------------------------------------- repair of lines missing from the INE copy

TOK = re.compile(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def an_flat() -> str:
    """The Asamblea Nacional 1999 text as one string of body paragraphs (headings dropped)."""
    s = pdftotext(SRC_AN_1999)
    s = s[s.rindex("\n", 0, s.index("Preámbulo")) + 1:s.index("Aprobada por el pueblo de Venezuela")]
    return " ".join(t for kind, t in paragraphs(layout_lines(s)) if kind == "p")


def repair_missing_lines(units: dict) -> tuple[list[dict], list[tuple]]:
    """The INE copy of G.O. 5.908 lacks some lines (mostly the last line of a page: the
    words are not in the PDF at all). Align the 5.908 text word by word with the Asamblea
    Nacional text of 1999 and insert every run of words that only the AN text has, unless
    it is heading text (the AN layout does not always mark headings). A word whose first
    letter is missing in the INE copy ('ara' for 'Para') is also restored. Mutates units;
    returns (repairs, remaining differences), both listed in PROGRESS.md."""
    import difflib
    order = [k for k in sorted(units, key=sort_key) if k not in ("titulos", "promulgacion")]
    a_toks = []  # (key, line, start, end, word)
    for k in order:
        for li, line in enumerate(units[k]["lines"]):
            for m in TOK.finditer(line):
                a_toks.append((k, li, m.start(), m.end(), m.group(0).lower()))
    an = an_flat()
    b_toks = [(m.start(), m.end(), m.group(0).lower()) for m in TOK.finditer(an)]
    heads = [" ".join(words(h)) for h in units["titulos"]["lines"]]
    sm = difflib.SequenceMatcher(a=[t[4] for t in a_toks], b=[t[2] for t in b_toks], autojunk=False)
    edits = []  # (key, line, pos_start, pos_end, replacement, record)
    other = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            frag = an[b_toks[j1][0]:(b_toks[j2][0] if j2 < len(b_toks) else len(an))].strip()
            frag = re.sub(r"\s*\d{1,2}\.$", "", frag).strip()  # never carry the next item's number
            fw = " ".join(words(frag))
            if any(f" {fw} " in f" {h} " for h in heads):
                other.append(("heading-only in AN", "", frag))
                continue
            k, li, st, en, _ = a_toks[i1 - 1]
            line = units[k]["lines"][li]
            cut = en
            while cut < len(line) and not line[cut].isspace():
                cut += 1
            edits.append((k, li, cut, cut, " " + frag,
                          {"unit": k, "kind": "missing words", "after": line[max(0, cut - 40):cut].strip(), "inserted": frag}))
            continue
        if tag == "replace" and i2 - i1 == 1 and j2 - j1 == 1:
            aw, bw = a_toks[i1][4], b_toks[j1][2]
            if len(bw) == len(aw) + 1 and bw.endswith(aw):
                k, li, st, en, _ = a_toks[i1]
                orig = an[b_toks[j1][0]:b_toks[j1][1]]
                edits.append((k, li, st, en, orig,
                              {"unit": k, "kind": "missing first letter", "was": units[k]["lines"][li][st:en], "now": orig}))
                continue
        other.append((tag, " ".join(t[4] for t in a_toks[i1:i2]), " ".join(t[2] for t in b_toks[j1:j2])))
    for k, li, p0, p1, rep, _ in sorted(edits, key=lambda e: (e[0], e[1], e[2]), reverse=True):
        line = units[k]["lines"][li]
        units[k]["lines"][li] = (line[:p0] + rep + line[p1:]).rstrip()
    return [e[5] for e in edits], other


# ---------------------------------------------------------------- independent cross-checks

def words(s: str) -> list[str]:
    s = norm(s).lower()
    return re.findall(r"[a-záéíóúüñ0-9]+", s)


def tsj_html_articles() -> dict[int, str]:
    b = cache_path(SRC_TSJ_HTML).read_bytes().decode("cp1252")
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", b)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return split_articles(s)


def an_1999_articles() -> dict[int, str]:
    s = pdftotext(SRC_AN_1999)
    s = re.sub(r"\s+", " ", s)
    return split_articles(s)


def split_articles(s: str, last: int = 350) -> dict[int, str]:
    """Split a flat text into articles 1..last by finding each 'Artículo N.' in order.

    Some transcriptions drop the word 'Artículo' before a number; then the bare
    'N. ' after a sentence end is accepted."""
    pos: list[tuple[int, int]] = []
    at = 0
    for n in range(1, last + 1):
        m = re.compile(rf"Art[íi]culo\s*{n}\s*[\.º°]").search(s, at)
        if not m:
            m = re.compile(rf"(?<=[\.:;]\s){n}\s*\.\s+(?=[A-ZÁÉÍÓÚ])").search(s, at)
        if not m:
            continue
        pos.append((n, m.start()))
        at = m.end()
    res: dict[int, str] = {}
    for i, (n, p0) in enumerate(pos):
        p1 = pos[i + 1][1] if i + 1 < len(pos) else len(s)
        res[n] = re.sub(rf"^Art[íi]culo\s*{n}\s*[\.º°]|^{n}\s*\.", "", s[p0:p1]).strip()
    return res


def verify(units: dict) -> list[str]:
    import difflib
    report = []
    for name, ref in (("TSJ HTML (G.O. 5.453)", tsj_html_articles()), ("AN PDF (1999 text)", an_1999_articles())):
        diffs = []
        for n in range(1, 351):
            k = f"art-{n:03d}"
            if k not in units or n not in ref:
                diffs.append((n, "missing"))
                continue
            a = words(re.sub(r"^Artículo \d+\.", "", units[k]["text"]))
            b = words(ref[n])
            if n == 350:
                b = b[:len(a)]
            if a != b:
                sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
                ops = [(t, " ".join(a[i1:i2]), " ".join(b[j1:j2])) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
                diffs.append((n, ops[:4]))
        report.append(f"{name}: {350 - len(diffs)}/350 articles word-identical; differing: {len(diffs)}")
        for n, ops in diffs:
            report.append(f"  art {n}: {ops}")
    return report


# ---------------------------------------------------------------- corpus

def build() -> dict:
    units, e_units, ver = parse_5908()
    repairs, _remaining = repair_missing_lines(units)
    arts = [k for k in units if k.startswith("art-")]
    assert len(arts) == 350, len(arts)
    assert ver == sorted(e_units), (ver, sorted(e_units))
    v1 = finish(units)
    u2 = {k: dict(v) for k, v in units.items()}
    for k, lines in e_units.items():
        u2[k] = dict(units[k])
        u2[k]["lines"] = lines
    v2 = finish(u2)
    changed = sorted(k for k in v1 if v1[k] != v2[k])
    assert changed == sorted(e_units), changed

    sha5908 = sha_of(SRC_5908)
    country = {
        "code": "VE", "name": "Venezuela", "slug": "venezuela", "lang": "es", "tz": "America/Caracas",
        "future_branch": "futuro",
        "publisher": {"name": "Imprenta Nacional y Gaceta Oficial", "email": "gaceta@gacetaoficial.invalid"},
        "default_in_force_rule": {
            "text": "Código Civil art. 1: \"La Ley es obligatoria desde su publicación en la GACETA OFICIAL o desde la fecha posterior que ella misma indique.\" A law's own vigencia clause overrides this.",
            "source": "https://historico.tsj.gob.ve/legislacion/ (Código Civil, G.O. 2.990 Ext., 26 Jul 1982)",
        },
        "licence_note": "Texto oficial publicado en la Gaceta Oficial de la República Bolivariana de Venezuela.",
    }
    reqs = sum(1 for _ in (CACHE / "requests.jsonl").open(encoding="utf-8"))
    sources = [
        {"name": "Gaceta Oficial N° 5.908 Extraordinario (19 Feb 2009), copy hosted by the Instituto Nacional de Estadística",
         "url": SRC_5908, "retrieved": DOCS_DATE, "requests": 1,
         "licence": "Official act of the State; Ley sobre el Derecho de Autor art. 11 is understood to exclude official acts from protection (not checked against the gazette here).",
         "notes": "Full reprint of the Constitution ordered by art. 2 of Enmienda N° 1, with '(Ver Enmienda N° 1 ...)' notes under arts. 160, 162, 174, 192 and 230, followed by the Enmienda. Text layer read with pdftotext."},
        {"name": "Tribunal Supremo de Justicia, constitucion1999.htm (TSJ transcription of G.O. 5.453 Ext., 24 Mar 2000), Wayback capture 2014-10-25",
         "url": SRC_TSJ_HTML, "retrieved": DOCS_DATE, "requests": 1,
         "licence": "Official text (as above).", "notes": "Used only to cross-check the 1999 text word by word."},
        {"name": "Asamblea Nacional, constitucion-nacional PDF (1999 text, G.O. 36.860 heading)",
         "url": SRC_AN_1999, "retrieved": DOCS_DATE, "requests": 1,
         "licence": "Official text (as above).", "notes": "Used only to cross-check the 1999 text word by word."},
        {"name": "Tribunal Supremo de Justicia, /constitucion and /codigos index pages",
         "url": SRC_TSJ_CONST_PAGE, "retrieved": DOCS_DATE, "requests": reqs - 3,
         "licence": "Official site.", "notes": "Index of official gazette PDFs (scans) and all other probe requests; every request is in .cache/requests.jsonl."},
    ]
    laws = {
        "constitucion-1999": {
            "label": "Constitución de 1999",
            "title": "Constitución de la República Bolivariana de Venezuela, aprobada por referendo el 15 de diciembre de 1999 y proclamada por la Asamblea Nacional Constituyente el 20 de diciembre de 1999",
            "kind": "referendum", "enacted": "1999-12-20", "published": "1999-12-30",
            "url": SRC_TSJ_CONST_PAGE, "temporary_until": None, "restores": None, "note": None},
        "enmienda-1-2009": {
            "label": "Enmienda N° 1",
            "title": "Enmienda N° 1 de la Constitución de la República Bolivariana de Venezuela, aprobada por el pueblo mediante referendo constitucional el 15 de febrero de 2009",
            "kind": "referendum", "enacted": "2009-02-15", "published": "2009-02-19",
            "url": SRC_5908, "temporary_until": None, "restores": None, "note": None},
    }
    const = {
        "slug": "constitucion", "short": "CRBV",
        "title": "Constitución de la República Bolivariana de Venezuela",
        "url": SRC_TSJ_CONST_PAGE,
        "first_law": "constitucion-1999", "earlier_laws": [],
        "versions": [
            {"from": "1999-12-30", "source_url": SRC_5908, "sha256": sha5908, "units": v1,
             "credits": {},
             "note": "Text of 1999 as reprinted in full in G.O. 5.908 Ext. (2009), whose body keeps the original wording of the five amended articles. It matches the TSJ transcription of the corrected reprint in G.O. 5.453 Ext. (24 Mar 2000); the uncorrected first printing in G.O. 36.860 (30 Dec 1999) has no text-layer copy, so its material errors are not shown."},
            {"from": "2009-02-19", "source_url": SRC_5908, "sha256": sha5908, "units": v2,
             "credits": {k: ["enmienda-1-2009"] for k in changed},
             "note": "Arts. 160, 162, 174, 192 and 230 as worded by Enmienda N° 1, published after the reprinted Constitution in the same gazette (Const. art. 341.5); the reprint keeps the old wording in the body with a '(Ver Enmienda N° 1 ...)' note."},
        ],
    }
    decisions = [
        "Constitution text: G.O. 5.908 Ext. of 19 Feb 2009 (the latest full official printing, ordered by Enmienda N° 1 art. 2), read from the text layer of the copy hosted by the Instituto Nacional de Estadística (ine.gob.ve). The TSJ and Asamblea Nacional copies of 5.908 and 5.453 are image scans and this machine has no OCR, so they were not used for text.",
        "Version 1 (from 1999-12-30) is the 5.908 body text with the original wording of arts. 160, 162, 174, 192 and 230 (which the reprint keeps, each followed by a '(Ver Enmienda N° 1 ...)' note, per Const. art. 341.5). It is cross-checked word by word against two independent official transcriptions of the 1999 text: the TSJ HTML of G.O. 5.453 and the Asamblea Nacional PDF; every difference is listed in PROGRESS.md.",
        "The original publication (G.O. 36.860, 30 Dec 1999) was reprinted 'por error material del ente emisor' in G.O. 5.453 Ext. (24 Mar 2000). No text-layer copy of 36.860 was found, so the corrections are not a separate version: version 1 carries the corrected wording from 1999-12-30 (its in-force day, Disposición final única).",
        "Version 2 (from 2009-02-19, the day of publication; the Enmienda names no other date, Código Civil art. 1) replaces the operative text of the five articles with the Enmienda's wording; the '(Ver Enmienda ...)' notes are dropped from the text.",
        "The Constitution of 1999 is credited as a referendum (approved 15 Dec 1999, proclaimed 20 Dec 1999); the Enmienda N° 1 as a referendum (approved 15 Feb 2009).",
        "One file per article, transitional provision, derogatory and final provision; the Preamble in preambulo.md; the closing approval paragraph in promulgacion.md; the headings of titles, chapters and sections, in order, in titulos.md. The lists of signatories are omitted. The Exposición de Motivos (in G.O. 5.453, not in 5.908) is not normative and is not included.",
        f"The INE copy of G.O. 5.908 lacks some lines of text (mostly the last line of a page; the words are not in the PDF). parse.py aligns it word by word with the Asamblea Nacional text and restores {len(repairs)} gaps from it, in units " + ", ".join(sorted({r['unit'] for r in repairs})) + ". Every restored passage is listed in PROGRESS.md. The remaining differences between the two are spellings of compound words ('politicoterritorial' in 5.908, 'político territorial' in the AN text) and two AN typos; the 5.908 spelling is kept.",
        "Paragraphs are rebuilt from the PDF layout: wrapped lines are joined, page numbers dropped, a blank line ends a paragraph only after . : ; or ), and numbered/lettered items start their own line. Spellings are kept as printed in G.O. 5.908.",
        f"PDF text extraction: {pdftotext_version()} with -enc UTF-8 -layout.",
    ]
    return {
        "country": country, "sources": sources, "laws": laws, "acts": [const], "applies": [],
        "decisions": decisions,
        "ai_use": ["none: no model wrote, summarised or corrected any legal text; parsing is rule-based (parse.py)."],
    }


def main() -> None:
    global OUT
    if "--out" in sys.argv:
        OUT = Path(sys.argv[sys.argv.index("--out") + 1])
    corpus = build()
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(OUT)
    a = corpus["acts"][0]
    print("wrote", OUT, "versions:", len(a["versions"]), "units:", len(a["versions"][-1]["units"]))
    if "--verify" in sys.argv:
        units, _, _ = parse_5908()
        repairs, remaining = repair_missing_lines(units)
        for r in repairs:
            print("REPAIR", json.dumps(r, ensure_ascii=False))
        for r in remaining:
            print("DIFF", r)


if __name__ == "__main__":
    main()
