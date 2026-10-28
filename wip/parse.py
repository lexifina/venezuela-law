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

ITEM_RE = re.compile(r"^(\d{1,2}|[a-zñ])(\.-|[\.\)])\s*(?=[A-ZÁÉÍÓÚÑa-záéíóúñ\"(])")
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


def paragraphs(lines: list[tuple[int, str]], extra_start: re.Pattern | None = None) -> list[tuple[str, str]]:
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
        starts_new = bool(ART_RE.match(t) or ORD_RE.match(t) or ITEM_RE.match(t) or t.startswith("(Ver Enmienda")
                         or (extra_start is not None and extra_start.match(t)))
        if cur and not starts_new:
            prev = cur[-1]
            ends = prev.rstrip()[-1:] in ".:;)"
            if pending_blank and ends and not t[:1].islower():
                flush()
        else:
            flush()
        cur.append(t)
        pending_blank = False
        if extra_start is not None and extra_start.match(t):
            flush()  # a standalone 'Artículo 1°' / 'Primera:' line is its own paragraph
    flush()
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


# ---------------------------------------------------------------- Constitution 1961 (TSJ text, as reprinted in 1983)

SRC_1961 = "https://web.archive.org/web/20110125000458id_/http://www.tsj.gov.ve:80/legislacion/constitucion1961.pdf"
ORD_1961 = ["Primera", "Segunda", "Tercera", "Cuarta", "Quinta", "Sexta", "Séptima", "Octava", "Novena", "Décima",
            "Decimaprimera", "Decimasegunda", "Decimatercera", "Decimacuarta", "Decimaquinta", "Decimasexta",
            "Decimaséptima", "Decimaoctava", "Decimanovena", "Vigésima", "Vigesimaprimera", "Vigesimasegunda",
            "Vigesimatercera"]
ART61_RE = re.compile(r"^Artículo (\d+)\s*[°º]?\s*\*?$")
ORD61_RE = re.compile(r"^(" + "|".join(ORD_1961) + r"):$")
NOTE61_RE = re.compile(r"^\*?\s*(Ver Enmienda|Cumplida \(ver Enmienda)", re.I)


def _units_1961(paras, ordinal_re=None, prefix="art", label="Art.", kind="art"):
    units: dict[str, dict] = {}
    heads: list[str] = []
    key = None
    for k, t in paras:
        if k == "h":
            heads.append(t)
            continue
        if NOTE61_RE.match(t):
            continue  # the reprint's '* Ver Enmienda ...' and 'Cumplida (ver Enmienda ...)' notes
        m = ART61_RE.match(t)
        o = ordinal_re.match(t) if ordinal_re else None
        if m and not ordinal_re:
            n = int(m.group(1))
            key = f"{prefix}-{n:03d}"
            if key in units:
                raise SystemExit(f"1961: duplicate {key}")
            units[key] = {"label": f"{label} {n}", "kind": kind, "lines": [re.sub(r"\s*\*$", "", t)]}
        elif o:
            n = ORD_1961.index(o.group(1)) + 1
            key = f"disp-transitoria-{n:02d}"
            units[key] = {"label": f"Disposición transitoria {o.group(1).lower()}", "kind": "transitional", "lines": [t]}
        elif key:
            units[key]["lines"].append(re.sub(r"\s*\*$", "", t))
    return units, heads


def parse_1961() -> tuple[dict, dict, dict, list[str]]:
    """Return (body units of 1961, enmienda 1 units, enmienda 2 units, notes)."""
    text = pdftotext(SRC_1961)
    i_t1 = text.index("Título I. De la República")
    i_dada = text.index("Dada, firmada y sellada en el Palacio Federal Legislativo")
    i_e1 = text.index("Enmienda Número 1 de la Constitución")
    i_e1b = text.index("Enmienda Número 1 de la Constitución", i_e1 + 10)
    i_e1end = text.index("Imprímase íntegramente la Constitución seguida de la enmienda", i_e1b)
    i_e2 = text.index("Enmienda Número 2 de la Constitución")
    i_e2b = text.index("Enmienda Número 2 de la Constitución", i_e2 + 10)
    i_e2end = text.index("Imprimase íntegramente la Constitución seguida de la Enmienda", i_e2b)
    i_tr = text.index("Disposiciones Transitorias de la Constitución")
    i_trb = text.index("Disposiciones Transitorias de la Constitución", i_tr + 10)
    i_trend = text.index("Dado, firmado y sellado en el Palacio Federal Legislativo", i_trb)

    def cut(a, b):
        return text[text.rindex("\n", 0, a) + 1:b]

    start = re.compile(r"^(Artículo \d+\s*[°º]?\s*\*?$|(" + "|".join(ORD_1961) + r"):$)")
    body, heads = _units_1961(paragraphs(layout_lines(cut(i_t1, i_dada)), start))
    i_pre = text.index("Requerido el voto de las Asambleas Legislativas")
    pre = norm(re.sub(r"\s+", " ", text[i_pre:text.index("Constitución de la República de Venezuela", i_pre)]))
    body["preambulo"] = {"label": "Preámbulo", "kind": "preamble", "lines": [pre, "Constitución de la República de Venezuela"]}
    closing = norm(re.sub(r"\s+", " ", text[i_dada:text.index("El Presidente del Congreso Nacional", i_dada)]))
    body["promulgacion"] = {"label": "Sanción", "kind": "closing", "lines": [closing]}
    trans, _ = _units_1961(paragraphs(layout_lines(cut(i_trb, i_trend)), start), ordinal_re=ORD61_RE)
    body.update(trans)
    body["titulos"] = {"label": "Títulos y capítulos", "kind": "heading",
                       "lines": [h for h in heads if not h.startswith(("Disposiciones Transitorias", "Constitución de la República"))]}
    e1, _ = _units_1961(paragraphs(layout_lines(cut(i_e1b, i_e1end)), start), prefix="enmienda-01-art", label="Enmienda N° 1, art.")
    e2, _ = _units_1961(paragraphs(layout_lines(cut(i_e2b, i_e2end)), start), prefix="enmienda-02-art", label="Enmienda N° 2, art.")
    # the cut ends just after the 'Artículo 2°' / 'Artículo 9°' line that orders the reprint; drop it
    e1 = {k: v for k, v in e1.items() if len(v["lines"]) > 1}
    e2 = {k: v for k, v in e2.items() if len(v["lines"]) > 1}
    return body, e1, e2, []


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
                          {"unit": k, "kind": "missing words", "after": (re.sub(r"^\S*\s", "", line[cut - 45:cut]) if cut > 45 else line[:cut]).strip(), "inserted": frag}))
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
             "note": "Text of 1999 as reprinted in full in G.O. 5.908 Ext. (2009), whose body keeps the original wording of the five amended articles. Checked word by word against the Asamblea Nacional's text of 1999, which also fills the lines missing from the INE copy of 5.908. The wording is that of the corrected reprint in G.O. 5.453 Ext. (24 Mar 2000); the first printing in G.O. 36.860 (30 Dec 1999) has no machine-readable copy, so its material errors are not shown."},
            {"from": "2009-02-19", "source_url": SRC_5908, "sha256": sha5908, "units": v2,
             "credits": {k: ["enmienda-1-2009"] for k in changed},
             "note": "Arts. 160, 162, 174, 192 and 230 as worded by Enmienda N° 1, published after the reprinted Constitution in the same gazette (Const. art. 341.5); the reprint keeps the old wording in the body with a '(Ver Enmienda N° 1 ...)' note."},
        ],
    }
    # ---- Constitución de 1961 (repealed 1999), TSJ text-layer PDF of the 1983 reprint
    b61, e1, e2, _ = parse_1961()
    sha61 = sha_of(SRC_1961)
    v61a = finish(b61)
    v61b = finish({**b61, **e1})
    v61c = finish({**b61, **e1, **e2})
    laws.update({
        "constitucion-1961": {
            "label": "Constitución de 1961",
            "title": "Constitución de la República de Venezuela, sancionada por el Congreso el 23 de enero de 1961 con el voto de las Asambleas Legislativas de los Estados",
            "kind": "law", "enacted": "1961-01-23", "published": "1961-01-23",
            "url": "https://historico.tsj.gob.ve/legislacion/constituciones/26461_GO.pdf", "temporary_until": None, "restores": None, "note": None},
        "enmienda-1-1973": {
            "label": "Enmienda N° 1 de 1973",
            "title": "Enmienda Número 1 de la Constitución, sancionada el 9 de mayo de 1973",
            "kind": "law", "enacted": "1973-05-09", "published": "1973-05-11",
            "url": "https://historico.tsj.gob.ve/legislacion/constituciones/1585_GOE.pdf", "temporary_until": None, "restores": None,
            "note": None},
        "enmienda-2-1983": {
            "label": "Enmienda N° 2 de 1983",
            "title": "Enmienda Número 2 de la Constitución, sancionada el 16 de marzo de 1983",
            "kind": "law", "enacted": "1983-03-16", "published": "1983-03-26",
            "url": "https://historico.tsj.gob.ve/legislacion/constituciones/32696_GOE.pdf", "temporary_until": None, "restores": None,
            "note": None},
    })
    c61 = {
        "slug": "constitucion-1961", "short": "CRV 1961",
        "title": "Constitución de la República de Venezuela (1961)",
        "url": SRC_TSJ_CONST_PAGE,
        "first_law": "constitucion-1961", "earlier_laws": [],
        "versions": [
            {"from": "1961-01-23", "source_url": SRC_1961, "sha256": sha61, "units": v61a, "credits": {},
             "note": "Text of 1961 as reprinted after Enmienda N° 2 (1983), transcribed by the Tribunal Supremo de Justicia. The enmiendas of this Constitution add separate texts and do not change the wording of its articles (art. 245.6). Arts. 191 and 192 are missing from the TSJ transcription, so they are not in this record."},
            {"from": "1973-05-11", "source_url": SRC_1961, "sha256": sha61, "units": v61b,
             "credits": {k: ["enmienda-1-1973"] for k in e1},
             "note": "Enmienda N° 1 is published after the Constitution and noted under arts. 149, 152, 182 and 213, whose words it does not change."},
            {"from": "1983-03-26", "source_url": SRC_1961, "sha256": sha61, "units": v61c,
             "credits": {k: ["enmienda-2-1983"] for k in e2},
             "note": "Enmienda N° 2 is published after the Constitution and noted under arts. 113, 122, 136, 139, 154, 156, 166, 167, 185, 227, 228 and 231, whose words it does not change."},
            {"from": "1999-12-30", "source_url": SRC_5908, "sha256": sha5908, "units": {},
             "credits": {k: ["constitucion-1999"] for k in v61c},
             "note": "Repealed by the Disposición derogatoria única of the Constitution of 1999: 'Queda derogada la Constitución de la República de Venezuela decretada el veintitrés de enero de mil novecientos sesenta y uno.'"},
        ],
    }
    sources.insert(3, {"name": "Tribunal Supremo de Justicia, constitucion1961.pdf (the 1961 text as reprinted after Enmienda N° 2 of 1983, with both enmiendas), Wayback capture 2011-01-25",
                       "url": SRC_1961, "retrieved": DOCS_DATE, "requests": 1, "licence": "Official text (as above).",
                       "notes": "Text-layer PDF from the TSJ's former site tsj.gov.ve. No second source to cross-check; arts. 191-192 are missing from it."})
    sources[-1]["requests"] -= 1

    decisions = [
        "Constitution text: G.O. 5.908 Ext. of 19 Feb 2009 (the latest full official printing, ordered by Enmienda N° 1 art. 2), read from the text layer of the copy hosted by the Instituto Nacional de Estadística (ine.gob.ve). The TSJ and Asamblea Nacional copies of 5.908 and 5.453 are image scans and this machine has no OCR, so they were not used for text.",
        "Version 1 (from 1999-12-30) is the 5.908 body text with the original wording of arts. 160, 162, 174, 192 and 230 (which the reprint keeps, each followed by a '(Ver Enmienda N° 1 ...)' note, per Const. art. 341.5). It is cross-checked word by word against the Asamblea Nacional's text of 1999 (a text-layer PDF). The TSJ's HTML transcription labelled G.O. 5.453 differs in wording from both in more than 80 articles and is not used.",
        "The original publication (G.O. 36.860, 30 Dec 1999) was reprinted 'por error material del ente emisor' in G.O. 5.453 Ext. (24 Mar 2000). No text-layer copy of 36.860 was found, so the corrections are not a separate version: version 1 carries the corrected wording from 1999-12-30 (its in-force day, Disposición final única).",
        "Version 2 (from 2009-02-19, the day of publication; the Enmienda names no other date, Código Civil art. 1) replaces the operative text of the five articles with the Enmienda's wording; the '(Ver Enmienda ...)' notes are dropped from the text.",
        "The Constitution of 1999 is credited as a referendum (approved 15 Dec 1999, proclaimed 20 Dec 1999); the Enmienda N° 1 as a referendum (approved 15 Feb 2009).",
        "One file per article, transitional provision, derogatory and final provision; the Preamble in preambulo.md; the closing approval paragraph in promulgacion.md; the headings of titles, chapters and sections, in order, in titulos.md. The lists of signatories are omitted. The Exposición de Motivos (in G.O. 5.453, not in 5.908) is not normative and is not included.",
        f"The INE copy of G.O. 5.908 lacks some lines of text (mostly the last line of a page; the words are not in the PDF). parse.py aligns it word by word with the Asamblea Nacional text and restores {len(repairs)} gaps from it, in units " + ", ".join(sorted({r['unit'] for r in repairs})) + ". Every restored passage is listed below. The remaining differences between the two are spellings of compound words ('politicoterritorial' in 5.908, 'político territorial' in the AN text) and AN typos ('postrado', 'contenciosa electoral', 'auditoria'); the 5.908 spelling is kept.",
        *[(f"Restored in {r['unit']} from the AN text, after '{r['after']}': '{r['inserted']}'." if r["kind"] == "missing words"
           else f"Restored in {r['unit']} from the AN text: '{r['was']}' is '{r['now']}' (first letter missing in the INE copy).") for r in repairs],
        "Paragraphs are rebuilt from the PDF layout: wrapped lines are joined, page numbers dropped, a blank line ends a paragraph only after . : ; or ), and numbered/lettered items start their own line. Spellings are kept as printed in G.O. 5.908.",
        "Constitución de 1961: text from the TSJ's text-layer PDF of the 1961 Constitution as reprinted after Enmienda N° 2 (Wayback capture 20110125000458 of tsj.gov.ve/legislacion/constitucion1961.pdf). The gazettes themselves (TSJ historico PDFs 26461_GO, 1585_GOE, 32696_GOE) are scans and were not read; the in-force days are the promulgation days printed in the text ('Ejecútese' 23 Jan 1961, 'Cúmplase' 11 May 1973 and 26 Mar 1983), taken as the days of publication in the Gaceta Oficial.",
        "Constitución de 1961: its enmiendas are separate texts published after the Constitution with a note under the articles they concern (art. 245.6); they do not change the articles' words. Each enmienda's operative articles are units of their own (enmienda-01-art-001, enmienda-02-art-001 to -008), added on its day; the reprint's notes '* Ver Enmienda ...' and 'Cumplida (ver Enmienda número 2 ...)' under fulfilled transitional provisions are dropped from the text.",
        "Constitución de 1961: arts. 191 and 192 are missing from the TSJ transcription (art. 190 runs straight into Capítulo III and art. 193), and no other machine-readable official copy was found, so they are absent from every version. The Disposiciones Transitorias (a separate text sanctioned on the same day, art. 251) are included as disp-transitoria-01 to -23. The signatories are omitted.",
        "Constitución de 1961: repealed on 1999-12-30 by the Disposición derogatoria única of the Constitution of 1999; that commit removes every file of constitucion-1961/ and is credited to the Constitution of 1999.",
        f"PDF text extraction: {pdftotext_version()} with -enc UTF-8 -layout.",
    ]
    return {
        "country": country, "sources": sources, "laws": laws, "acts": [const, c61], "applies": [],
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
