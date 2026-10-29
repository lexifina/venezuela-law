"""Codes and laws from born-digital Gaceta Oficial PDFs -> corpus.d parts (gitlaw_common/SCHEMA.md).

Reads only .cache/ (no network). The text is what the gazette page prints, taken from its text
layer by gazette_text.py (clipped and painted-over text dropped; no OCR). corpus.json (the
Constitutions, parse.py) is not touched. Each act is its own part, corpus.d/<NN>-<act>.json,
verified on its own (corpus.d/<NN>-<act>.PUBLISH); corpus.d/30-gaceta-digital.json holds the
decisions they share.

    python -X utf8 parse_codes.py                 write every part (atomically)
    python -X utf8 parse_codes.py --out DIR       write the parts into DIR instead of corpus.d/
    python -X utf8 parse_codes.py --check         also print item-sequence checks
    python -X utf8 parse_codes.py --verify        also cross-check each act's words against the gazette
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import gazette_text
from parse import ORDINALS, cache_path, norm, sha_of

HERE = Path(__file__).resolve().parent
OUT = HERE / "corpus.d"
RETRIEVED = "2026-10-28"
GACETA = "http://www.gacetaoficial.gob.ve/"

ART_RE = re.compile(r"^Artículos? (\d+)\s*[º°]?(?:-([A-Z]))?-?(?:\s*\.+-?\s*(?=\S)|\s+(?=[A-ZÁÉÍÓÚÑ])|$)")  # 'Artículo 139' alone on its line (COP)
ART_GLUED = re.compile(r"^(Artículo \d+\s*[º°]?\.)(?=[A-ZÁÉÍÓÚÑ])")
ITEM_RE = re.compile(r"^(\d{1,2}|[a-zñ])(\.-|[\.\)])\s*(?=[A-ZÁÉÍÓÚÑa-záéíóúñ\"“(])")
ORD_RE = re.compile(r"^(" + "|".join(ORDINALS) + r"|Única|Unica)\s*[\.:]-?\s*(?=\S)", re.I)
STRUCT_RE = re.compile(r"^(LIBRO|T[IÍ]TULO|CAP[IÍ]TULO|Cap[ií]tulo|SECCI[OÓ]N|Secci[oó]n|DISPOSICI[OÓ]N|DISPOSICIONES|Disposici[oó]n|Disposiciones)\b")
LABEL_RE = re.compile(r"(LIBRO|T[IÍ]TULO|CAP[IÍ]TULO|Cap[ií]tulo|SECCI[OÓ]N|Secci[oó]n)\b")


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


ORD_INDEX = {_fold(w): i + 1 for i, w in enumerate(ORDINALS)} | {"unica": 1}


# ---------------------------------------------------------------- printed lines -> paragraphs

def join_lines(lines: list[str]) -> str:
    s = ""
    for t in lines:
        if s.endswith("-") and len(s) > 1 and s[-2].isalpha():
            s += t  # 'Político-' + 'Administrativa'
        else:
            s = (s + " " + t) if s else t
    return ART_GLUED.sub(lambda m: m.group(1) + " ", norm(s))


def margins(col: gazette_text.Column) -> tuple[float, float]:
    """The column's text margins: the lowest decile of line starts and the highest decile of line
    ends, so a stray line wider than the column does not move them, nor do indented items."""
    if len(col.lines) < 10:
        return col.left, col.right
    x0 = sorted(l.x0 for l in col.lines)
    x1 = sorted(l.x1 for l in col.lines)
    return x0[len(x0) // 10], x1[(9 * len(x1)) // 10]


def right_epigraph_lines(cols: list[gazette_text.Column]) -> set[tuple[int, int]]:
    """(column, line) indices of article epigraphs set flush right that may be long or wrap (gazettes
    of 2021 on): the run of up to four lines just before an 'Artículo N.' line, each set flush against
    the right margin and in from the left one, none an article, item or ordinal and none ending in
    . : ;, where the line before the run ends a sentence (. : ;) or is a centred heading, or the run
    opens the act or a column."""
    flat = []
    for ci, col in enumerate(cols):
        left, right = margins(col)
        for li, ln in enumerate(col.lines):
            flat.append(((ci, li), ln.x0 - left, right - ln.x1, ln.text))
    out: set[tuple[int, int]] = set()
    for j, (_, _, _, t) in enumerate(flat):
        if not ART_RE.match(t):
            continue
        k = j - 1
        run = []
        while k >= 0 and len(run) < 4:
            idx, lo, ro, s = flat[k]
            if ro < 5 and lo > 2 and s[-1:] not in ".:;" and not (ART_RE.match(s) or ITEM_RE.match(s) or ORD_RE.match(s)):
                run.append(idx)
                k -= 1
            else:
                break
        if not run:
            continue
        if k < 0 or run[-1][1] == 0 or flat[k][3][-1:] in ".:;" or (flat[k][1] > 15 and abs(flat[k][1] - flat[k][2]) < 12):
            out.update(run)
    return out


def paragraphs(cols: list[gazette_text.Column], flush_sections: bool = False,
               right_epigraphs: bool = False) -> list[tuple[str, str]]:
    """[(kind, text)]: 'p' paragraph, 'h' heading (centred, or LIBRO/TÍTULO/Capítulo/... at the start
    of a paragraph), 'e' epigraph (a short line set flush right). A line ends a paragraph if it ends
    with . : ; and stops well short of the right margin; numbered items and articles start their own
    paragraph; a line in lower case at the top of a column continues the paragraph before it."""
    out: list[tuple[str, str]] = []
    cur: list[str] = []
    wrapping = False

    def flush():
        nonlocal cur
        if cur:
            out.append(("p", join_lines(cur)))
            cur = []

    epi_lines = right_epigraph_lines(cols) if right_epigraphs else set()
    for ci, col in enumerate(cols):
        left, right = margins(col)
        width = right - left
        for li, ln in enumerate(col.lines):
            lo, ro, t = ln.x0 - left, right - ln.x1, ln.text
            t = re.sub(r"^A rtículo(s?) (?=\d)", r"Artículo\1 ", t)  # kerned 'A' read as a separate glyph (LOA art. 55)
            if (ci, li) in epi_lines:
                flush()
                if out and out[-1][0] == "e":
                    out[-1] = ("e", out[-1][1] + " " + norm(t))
                else:
                    out.append(("e", norm(t)))
                continue
            special = ART_RE.match(t) or ITEM_RE.match(t) or ORD_RE.match(t)
            if out and out[-1][0] == "h" and not cur and not special and lo > 1.0 and ro > 1.0 and abs(lo - ro) < 3:
                # a heading's name wide enough to fill the column, set in from both margins
                if wrapping and not STRUCT_RE.match(t):
                    out[-1] = ("h", out[-1][1] + " " + norm(t))
                else:
                    out.append(("h", norm(t)))
                wrapping = True
                continue
            numbered_head = ITEM_RE.match(t) and not ART_RE.match(t) and lo > 30 and abs(lo - ro) < 12  # '2. De la Acusación' (COJM)
            if lo > 15 and abs(lo - ro) < 12 and (not special or numbered_head) and (not cur or lo > 30):
                # centred (an item's hanging-indent last line can look centred: not inside a paragraph)
                flush()
                if wrapping and not STRUCT_RE.match(t):
                    out[-1] = ("h", out[-1][1] + " " + norm(t))  # the last line of a wrapped heading
                else:
                    out.append(("h", norm(t)))
                wrapping = False
                continue
            wrapping = False
            if flush_sections and lo > 25 and ro < 15 and any(rx.match(t) for _, rx in SECTIONS):
                # 'Disposición Transitoria' etc. set flush right like an epigraph (LOZEE): a heading
                flush()
                out.append(("h", norm(t)))
                continue
            if lo > 25 and ro < 15 and len(t) < 80 and not special and not cur:
                flush()
                if out and out[-1][0] == "e":
                    out[-1] = ("e", out[-1][1] + " " + norm(t))
                else:
                    out.append(("e", norm(t)))
                continue
            if STRUCT_RE.match(t) and not cur and not t.endswith("."):
                out.append(("h", norm(t)))
                continue
            if t[:1].islower() and not cur and out and out[-1][0] == "p" and not ITEM_RE.match(t):
                cur = [out.pop()[1]]  # continues the paragraph before (page or column break)
            elif special:
                flush()
            cur.append(t)
            if t[-1:] in ".:;" and ro > 0.1 * width:
                flush()
    flush()
    return out


def group_headings(hs: list[str]) -> list[str]:
    """'TÍTULO I' + 'Disposiciones Preliminares' -> 'TÍTULO I. Disposiciones Preliminares'."""
    out: list[str] = []
    for h in hs:
        if out and re.fullmatch(r"(LIBRO \w+|T[IÍ]TULO [IVXL]+|T[IÍ]TULO PRELIMINAR|T[ií]tulo Preliminar|CAP[IÍ]TULO [IVXL]+|Cap[ií]tulo [IVXL]+|Secci[oó]n \w+( Primera| Segunda| Tercera| Cuarta| Quinta)?|SECCI[OÓ]N \w+)", out[-1]) \
                and not LABEL_RE.match(h):
            out[-1] = out[-1] + ". " + h
        else:
            out.append(h)
    return out


SECTIONS = [("trans", re.compile(r"^DISPOSICI[OÓ]N(ES)? TRANSITORIA", re.I)),
            ("derog", re.compile(r"^DISPOSICI[OÓ]N(ES)? DEROGATORIA", re.I)),
            ("final", re.compile(r"^DISPOSICI[OÓ]N(ES)? FINAL", re.I))]
SEC_NAME = {"trans": ("disp-transitoria", "Disposición transitoria", "transitional"),
            "derog": ("disp-derogatoria", "Disposición derogatoria", "repeal"),
            "final": ("disp-final", "Disposición final", "final")}


def units_from(paras: list[tuple[str, str]], act: str) -> dict[str, dict]:
    """Articles art-NNN (epigraph, if any, as the first line), dispositions by section and ordinal
    (disp-transitoria-01 ...), and the headings in order in 'titulos'."""
    units: dict[str, dict] = {}
    heads: list[str] = []
    pending: list = []
    key = None
    section = "body"
    for kind, t in paras:
        if kind in ("h", "e"):
            pending.append((kind, t))
            continue
        m, o = ART_RE.match(t), ORD_RE.match(t)
        for k, h in pending:
            for name, rx in SECTIONS:
                if k == "h" and rx.match(h):
                    section = name
        if m or (o and section != "body"):
            epi = [h for k, h in pending if k == "e"]
            heads.extend(h for k, h in pending if k == "h")
            pending = []
            if m:
                n, suf = int(m.group(1)), m.group(2)
                key, label, ukind = f"art-{n:03d}", f"Art. {n}", "art"
                if suf:  # 'Artículo 126-A' (inserted by a reform)
                    key, label = f"{key}-{suf.lower()}", f"{label}-{suf}"
            else:
                n = ORD_INDEX[_fold(o.group(1))]
                base, lab, ukind = SEC_NAME[section]
                key = f"{base}-{n:02d}"
                label = f"{lab} {'única' if _fold(o.group(1)) == 'unica' else ORDINALS[n - 1].lower()}"
            if key in units:
                raise SystemExit(f"{act}: duplicate {key}: {t[:60]}")
            units[key] = {"label": label, "kind": ukind, "lines": [" ".join(epi)] if epi else []}
            units[key]["lines"].append(t)
        else:
            if pending:  # a heading-like line inside an article: keep it as text
                if key is None:
                    raise SystemExit(f"{act}: text before the first article: {pending}")
                units[key]["lines"].extend(h for k, h in pending)
                pending = []
            if key is None:
                raise SystemExit(f"{act}: text before the first article: {t[:60]}")
            units[key]["lines"].append(t)
    if pending:
        raise SystemExit(f"{act}: trailing headings {pending}")
    units["titulos"] = {"label": "Libros, títulos, capítulos y secciones", "kind": "heading",
                        "lines": group_headings(heads)}
    return units


def finish(units: dict) -> dict:
    order = {"disp-transitoria": 2, "disp-derogatoria": 3, "disp-final": 4, "titulos": 9}

    def sk(k):
        if k.startswith("art-"):
            return (1, int(k[4:7]), k)
        base = k.rsplit("-", 1)[0] if k[-1].isdigit() else k
        return (order.get(base, 8), 0, k)
    return {k: {"label": units[k]["label"], "kind": units[k]["kind"], "text": "\n".join(units[k]["lines"]) + "\n"}
            for k in sorted(units, key=sk)}


def cut(cols: list[gazette_text.Column], start: str, end: str) -> list[gazette_text.Column]:
    """The columns from the line equal to `start` (exclusive) to the first later line starting with `end` (exclusive)."""
    pos = [(ci, li) for ci, c in enumerate(cols) for li in range(len(c.lines))]
    s = next(p for p in pos if cols[p[0]].lines[p[1]].text == start)
    e = next(p for p in pos if p > s and cols[p[0]].lines[p[1]].text.startswith(end))
    out = []
    for ci in range(s[0], e[0] + 1):
        c = cols[ci]
        a = s[1] + 1 if ci == s[0] else 0
        b = e[1] if ci == e[0] else len(c.lines)
        out.append(gazette_text.Column(c.page, c.side, c.left, c.right, c.lines[a:b]))
    return out


def check_sequence(units: dict, act: str, last: int) -> list[str]:
    arts = sorted(int(k[4:7]) for k in units if k.startswith("art-") and len(k) == 7)
    if arts == list(range(1, last + 1)):
        return []
    miss = sorted(set(range(1, last + 1)) - set(arts))
    return [f"{act}: articles missing {miss[:20]}, extra {[a for a in arts if a > last]}"]


def items_check(units: dict) -> list[str]:
    """Numbered items in each unit must run 1, 2, 3 ... (restarting at 1 is allowed)."""
    out = []
    for k, u in units.items():
        prev = 0
        for l in u["lines"]:
            m = re.match(r"^(\d{1,2})\.\s", l)
            if m:
                n = int(m.group(1))
                if n != prev + 1 and n != 1:
                    out.append(f"{k}: item {n} after {prev}")
                prev = n
    return out


TOK = re.compile(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñºª°]+")
HDR = {"N", "Extraordinario", "GACETA", "OFICIAL", "DE", "LA", "REPÚBLICA", "BOLIVARIANA", "VENEZUELA"}


def act_columns(spec: dict, filtered: bool = True) -> list[gazette_text.Column]:
    """The act's printed columns, plus any passage listed in spec['restore']: (page, side, first words)
    of text that the text layer holds below the page's bottom edge, where the frame cut it off and no
    later page prints it (the passage, from that line to the column's end, is put back)."""
    single = frozenset(spec.get("single", ()))  # pages set in one full-width column
    cols = gazette_text.visible_columns(cache_path(spec["url"]), filtered=filtered, single=single)
    if filtered and spec.get("restore"):
        raw = {(c.page, c.side): c for c in gazette_text.visible_columns(cache_path(spec["url"]), filtered=False, single=single)}
        for page, side, first, *count in spec["restore"]:  # count: restore only that many lines
            col = next(c for c in cols if (c.page, c.side) == (page, side))
            src = raw[(page, side)].lines
            i = next(i for i, l in enumerate(src) if l.text.startswith(first))
            assert all(l.text != src[i].text for l in col.lines), (spec["short"], first)
            col.lines = sorted(col.lines + src[i:i + count[0] if count else None], key=lambda l: l.y)
    if filtered:
        # spec['skip']: (page, side, first words) of a passage the gazette prints twice in a row; its
        # first printing, from that line to the column's end, is read once (the second printing stays)
        for page, side, first in spec.get("skip", ()):
            col = next(c for c in cols if (c.page, c.side) == (page, side))
            i = next(i for i, l in enumerate(col.lines) if l.text.startswith(first))
            col.lines = col.lines[:i]
        # spec['furniture']: a regex for printed fragments of page furniture that a white box covers
        # only in part (for example 'Pá i 29 d 83', what shows of a 'Página 29 de 83' footer)
        if spec.get("furniture"):
            rx = re.compile(spec["furniture"])
            for c in cols:
                c.lines = [l for l in c.lines if not rx.fullmatch(l.text)]
    return [c for c in cut(cols, *spec["cut"])]


def verify(spec: dict, units: dict) -> list[str]:
    """Cross-checks of one act against its gazette:
    1. the words of the units are exactly the words printed in the act's part of the gazette (as multisets);
    2. every run of words in the text layer that was dropped as not printed is listed, with whether
       the same words are printed elsewhere in the act (frame overflow repeated on the next page)."""
    import difflib
    from collections import Counter
    vis = [w for c in act_columns(spec) for l in c.lines for w in TOK.findall(re.sub(r"^A rtículo", "Artículo", l.text))]
    allw = [w for c in act_columns(spec, filtered=False) for l in c.lines for w in TOK.findall(l.text)]
    got = [w for u in units.values() for w in TOK.findall("\n".join(u["lines"]))]
    out = []
    a, b = Counter(vis), Counter(got)
    if a != b:
        out.append(f"WORDS DIFFER: printed-not-in-units {dict((a - b).most_common(10))} units-not-printed {dict((b - a).most_common(10))}")
    else:
        out.append(f"words: units == printed text ({len(got)} words)")
    sm = difflib.SequenceMatcher(None, allw, vis, autojunk=False)
    visj = " " + " ".join(w for w in vis if w not in HDR and not w.isdigit()) + " "
    dropped = elsewhere = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        gone = allw[i1:i2]
        if op == "insert" or not gone:
            out.append(f"INSERTED? {' '.join(vis[j1:j2])[:120]}")
            continue
        dropped += len(gone)
        # printed elsewhere: the run's 5-word chunks are printed in the act, ignoring the running header
        # and numbers; the header is sometimes interleaved letter by letter with an overflow line, so
        # 3 chunks in 4 suffice
        g = [w for w in gone if w not in HDR and not w.isdigit()]
        chunks = [c for c in ([g[k:k + 5] for k in range(0, max(len(g) - 4, 1))] if len(g) > 5 else [g]) if c]
        found = sum((" " + " ".join(c) + " ") in visj for c in chunks)
        dup = found >= 0.75 * len(chunks) or op == "replace" and "".join(gone) == "".join(vis[j1:j2])
        elsewhere += len(gone) if dup else 0
        out.append(f"dropped {len(gone):4d} words ({'printed elsewhere' if dup else 'NOT printed elsewhere'}): {' '.join(gone)[:150]}"
                   + (f" | replaced by: {' '.join(vis[j1:j2])[:80]}" if op == "replace" else ""))
    out.append(f"dropped from the text layer: {dropped} words, of which {elsewhere} are printed elsewhere")
    return out


# ---------------------------------------------------------------- the acts

def gazette_source(number: str, day: str, url: str, contents: str) -> dict:
    return {"name": f"Gaceta Oficial N° {number} ({day}), Imprenta Nacional portal gacetaoficial.gob.ve",
            "url": url, "retrieved": RETRIEVED, "requests": 1,
            "licence": "Official act of the State, published by the Servicio Autónomo Imprenta Nacional y Gaceta Oficial (official acts are understood to be outside copyright under Venezuelan law; not checked against the statute here).",
            "notes": contents + " Born-digital PDF; read from its text layer with gazette_text.py."}


def law(label: str, title: str, kind: str, enacted: str, published: str, url: str) -> dict:
    return {"label": label, "title": title, "kind": kind, "enacted": enacted, "published": published,
            "url": url, "temporary_until": None, "restores": None, "note": None}


ACTS = [
    {"part": "31-copp", "slug": "codigo-organico-procesal-penal", "short": "COPP", "title": "Código Orgánico Procesal Penal",
     "url": GACETA + "storage/2022/T028700036796-0-6.644_17-09-2021-000.pdf",
     "cut": ("CÓDIGO ORGÁNICO PROCESAL PENAL", "Dada, firmada y sellada en el Palacio Federal Legislativo"), "last": 518,
     "from": "2021-09-17", "gazette": ("6.644 Extraordinario", "17 Sep 2021"),
     "law": ("lo-reforma-copp-2021", law("Ley Orgánica de Reforma del COPP (2021)", "Ley Orgánica de Reforma del Código Orgánico Procesal Penal, sancionada el 16 de septiembre de 2021", "law", "2021-09-16", "2021-09-17", GACETA + "storage/2022/T028700036796-0-6.644_17-09-2021-000.pdf")),
     "first_law": None,
     # the texts the 2021 Code replaces, as its Disposición derogatoria única names them, plus Decreto 9.042
     # of 2012, the text the Ley Orgánica de Reforma amends; their gazettes have no machine-readable text
     "earlier": [("copp-1998", "Código Orgánico Procesal Penal (1998)", "5.208 Extraordinario", "1998-01-23", "law"),
                 ("reforma-copp-2000", "Reforma del COPP (2000)", "37.002", "2000-08-25", "law"),
                 ("reforma-copp-2001", "Reforma del COPP (2001)", "5.552 Extraordinario", "2001-11-12", "law"),
                 ("reforma-copp-2006", "Reforma del COPP (2006)", "38.536", "2006-10-04", "law"),
                 ("reforma-copp-2008", "Reforma del COPP (2008)", "5.894 Extraordinario", "2008-08-26", "law"),
                 ("reforma-copp-2009", "Reforma del COPP (2009)", "5.930 Extraordinario", "2009-09-04", "law"),
                 ("decreto-9042-copp-2012", "Decreto N° 9.042, Código Orgánico Procesal Penal (2012)", "6.078 Extraordinario", "2012-06-15", "decree")],
     "contents": "Ley Orgánica de Reforma del Código Orgánico Procesal Penal followed by the texto único of the Code.",
     "note": "Texto único of the Código Orgánico Procesal Penal as reformed by the Ley Orgánica de Reforma of 2021, printed in full in G.O. 6.644 Ext. of 17 Sep 2021 and in force on publication (its Disposición final única). Earlier versions (1998-2012) survive only as image scans and are not in this record (no OCR).",
     "decisions": ["COPP: the Ley Orgánica de Reforma of 2021 is printed first in G.O. 6.644 Ext., then the Code in full ('texto único'); only the texto único is read, from its title to the closing 'Dada, firmada y sellada'. In force from publication, 2021-09-17 (Disposición final única). The first version is credited to the publisher as the oldest version available, naming the earlier COPP texts listed in its Disposición derogatoria única and the Decreto of 2012, because it is not the Code as first enacted. Arts. 1-518 and 126-A."]},
    {"part": "32-cot", "slug": "codigo-organico-tributario", "short": "COT", "title": "Código Orgánico Tributario",
     "url": GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf",
     "cut": ("CÓDIGO ORGÁNICO TRIBUTARIO", "Dado y firmada en la Asamblea Nacional Constituyente"), "last": 352,
     "from": "2020-02-28", "gazette": ("6.507 Extraordinario", "29 Jan 2020"),
     "law": ("decreto-constituyente-cot-2020", law("Decreto Constituyente del Código Orgánico Tributario (2020)", "Decreto Constituyente mediante el cual se dicta el Código Orgánico Tributario, de la Asamblea Nacional Constituyente, de 29 de enero de 2020", "decree", "2020-01-29", "2020-01-29", GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf")),
     "first_law": "decreto-constituyente-cot-2020", "earlier": [],
     "contents": "Decreto Constituyente mediante el cual se dicta el Código Orgánico Tributario (with other constituent decrees in the same issue).",
     "note": "The Código Orgánico Tributario dictated by Decreto Constituyente of the Asamblea Nacional Constituyente, G.O. 6.507 Ext. of 29 Jan 2020, in force thirty continuous days after publication (art. 352). It repeals the Código of 2014 (G.O. 6.152 Ext., art. 351), whose gazette is an image scan and is not in this record.",
     "decisions": ["COT: the Decreto Constituyente of 29 Jan 2020 dictates the whole Code (not a partial reform); in force thirty continuous days after publication, 2020-02-28 (art. 352); it repeals the Código of 2014 (art. 351). Credited to the decree as first_law, of kind 'decree'. Item 2 of art. 293 is printed empty and is kept so."]},
    {"part": "33-cop", "slug": "codigo-organico-penitenciario", "short": "COP", "title": "Código Orgánico Penitenciario",
     "url": GACETA + "storage/2021/T028700036804-0-GOE_6.647-000.pdf",
     "cut": ("Código Orgánico Penitenciario", "Dada, firmada y sellada en el Palacio Federal Legislativo"), "last": None,
     "from": "2021-09-17", "gazette": ("6.647 Extraordinario", "17 Sep 2021"),
     "law": ("ley-reforma-cop-2021", law("Ley de Reforma del Código Orgánico Penitenciario (2021)", "Ley de Reforma del Código Orgánico Penitenciario, sancionada el 16 de septiembre de 2021", "law", "2021-09-16", "2021-09-17", GACETA + "storage/2021/T028700036804-0-GOE_6.647-000.pdf")),
     "first_law": None, "earlier": [],
     "contents": "Ley de Reforma del Código Orgánico Penitenciario followed by the texto único of the Code.",
     "note": "Texto único of the Código Orgánico Penitenciario as reformed by the Ley de Reforma of 2021 (art. 9 orders the reprint), printed in G.O. 6.647 Ext. of 17 Sep 2021 and in force on publication (its Disposición final única). The Code's first text (2015) is not on the gazette portal and is not in this record.",
     "decisions": ["COP: the Ley de Reforma of 2021 (arts. 1-9) is printed first in G.O. 6.647 Ext., then the Code in full; only the texto único is read, from its title to the closing 'Dada, firmada y sellada'. In force from publication, 2021-09-17 (Disposición final única). Credited to the publisher as the oldest version available. The Code's 2015 text (G.O. 6.207 Ext.) is not indexed on the gazette portal (its 2015-12-28 index lists 40.817 and 6.208 only), so it is not here. Art. 139 is printed as 'Artículo 139' with no full stop and its text on the next line; it is kept so."]},
    {"part": "34-cojm", "slug": "codigo-organico-de-justicia-militar", "short": "COJM", "title": "Código Orgánico de Justicia Militar",
     "url": GACETA + "storage/2021/T028700036801-0-GOE_6.646-000.pdf",
     "cut": ("CODIGO ORGÁNICO DE JUSTICIA MILITAR", "Dada, firmada y sellada en el Palaci"), "last": None,
     "restore": [(9, 0, "Artículo 187.")],
     "from": "2021-09-17", "gazette": ("6.646 Extraordinario", "17 Sep 2021"),
     "law": ("lo-reforma-cojm-2021", law("Ley Orgánica de Reforma Parcial del COJM (2021)", "Ley Orgánica de Reforma Parcial del Código Orgánico de Justicia Militar, sancionada el 16 de septiembre de 2021", "law", "2021-09-16", "2021-09-17", GACETA + "storage/2021/T028700036801-0-GOE_6.646-000.pdf")),
     "first_law": None, "earlier": [],
     "contents": "Ley Orgánica de Reforma Parcial del Código Orgánico de Justicia Militar followed by the texto único of the Code.",
     "note": "Texto único of the Código Orgánico de Justicia Militar as reformed by the Ley Orgánica de Reforma Parcial of 2021 (art. 8 orders the reprint), printed in G.O. 6.646 Ext. of 17 Sep 2021 and in force on publication (its Disposición final única). Earlier texts are not in this record.",
     "decisions": ["COJM: the Ley Orgánica de Reforma Parcial of 2021 is printed first in G.O. 6.646 Ext., then the Code in full; only the texto único is read. In force from publication, 2021-09-17 (Disposición final única). Credited to the publisher as the oldest version available; its earlier texts are image scans.",
                   "COJM art. 187 is restored from the text layer: its four lines sit below the bottom edge of page 9 (left column), outside the text frame, so the printed page omits them and page 9's right column goes on with art. 188. It is the only passage restored; every other word dropped from the text layer is printed elsewhere or is a hidden page header.",
                   "COJM: the heading 'CAPITULO III. De la Corte Suprema de Justicia' before art. 30 is in the text layer but painted over on the printed page, so it is not in titulos.md. Printed forms kept as they are: 'Artículos 304.' and 'Artículo 577-.'. Sub-headings numbered within a section ('1. De la Denuncia', '2. De la Acusación' ...) are headings in titulos.md."]},
    {"part": "35-lotsj", "slug": "ley-organica-del-tribunal-supremo-de-justicia", "short": "LOTSJ", "title": "Ley Orgánica del Tribunal Supremo de Justicia",
     "url": GACETA + "storage/2022/T028700037783-0-6.684_19-01-2022-000.pdf",
     "cut": ("LEY ORGÁNICA DEL TRIBUNAL SUPREMO DE JUSTICIA", "Dada, firmada y sellada en el Palacio Federal Legislativo"), "last": None,
     "from": "2022-01-19", "gazette": ("6.684 Extraordinario", "19 Jan 2022"),
     "law": ("lo-reforma-lotsj-2022", law("Ley Orgánica de Reforma de la LOTSJ (2022)", "Ley Orgánica de Reforma de la Ley Orgánica del Tribunal Supremo de Justicia, sancionada el 18 de enero de 2022", "law", "2022-01-18", "2022-01-19", GACETA + "storage/2022/T028700037783-0-6.684_19-01-2022-000.pdf")),
     "first_law": None, "earlier": [],
     "contents": "Ley Orgánica de Reforma de la Ley Orgánica del Tribunal Supremo de Justicia followed by the texto único of the Law.",
     "note": "Texto único of the Ley Orgánica del Tribunal Supremo de Justicia as reformed in 2022 (art. 16 of the reform orders the reprint), printed in G.O. 6.684 Ext. of 19 Jan 2022 and in force on publication (its Disposición final tercera). The Laws of 2004 and 2010 are image scans and are not in this record.",
     "decisions": ["LOTSJ: the Ley Orgánica de Reforma of 2022 is printed first in G.O. 6.684 Ext., then the Law in full; only the texto único is read. In force from publication, 2022-01-19 (Disposición final tercera). Credited to the publisher as the oldest version available; the 2010 Law (G.O. 39.483, reprinted 39.522) is an image scan."]},
    {"part": "36-iva", "slug": "ley-del-impuesto-al-valor-agregado", "short": "LIVA", "title": "Decreto con Rango, Valor y Fuerza de Ley que Establece el Impuesto al Valor Agregado",
     "url": GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf",
     "cut": ("EL IMPUESTO AL VALOR AGREGADO", "Dado y firmada en la Asamblea Nacional Constituyente"), "last": None,
     "from": "2020-03-29", "gazette": ("6.507 Extraordinario", "29 Jan 2020"),
     "law": ("decreto-constituyente-iva-2020", law("Decreto Constituyente de Reforma Parcial de la Ley del IVA (2020)", "Decreto Constituyente de Reforma Parcial del Decreto con Rango, Valor y Fuerza de Ley que Establece el Impuesto al Valor Agregado, de la Asamblea Nacional Constituyente, de 29 de enero de 2020", "decree", "2020-01-29", "2020-01-29", GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf")),
     "first_law": None, "earlier": [],
     "contents": "Decreto Constituyente de Reforma Parcial of the IVA law (art. 9 orders the reprint) followed by the texto único of the law.",
     "note": "Texto único of the Ley que Establece el Impuesto al Valor Agregado as reformed by Decreto Constituyente of 29 Jan 2020 (G.O. 6.507 Ext.), in force sixty continuous days after publication (art. 72 of the reprinted text). It repeals the reform of 2018 (G.O. 6.396 Ext., whose text pages are image scans); earlier texts are not in this record.",
     "decisions": ["LIVA: the Decreto Constituyente de Reforma Parcial of 29 Jan 2020 is printed in G.O. 6.507 Ext., followed by the law in full (its art. 9 orders a single text); only the texto único is read, from its title to the closing 'Dado y firmada'. In force sixty continuous days after publication, 2020-03-29 (art. 72, counted as for the COT's thirty days). Credited to the publisher as the oldest version available: the 2018 reform (G.O. 6.396 Ext.) has a text layer only on its first two pages."]},
    {"part": "37-loa", "slug": "ley-organica-de-aduanas", "short": "LOA", "title": "Decreto con Rango, Valor y Fuerza de Ley Orgánica de Aduanas",
     "url": GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf",
     "cut": ("LEY ORGÁNICA DE ADUANAS", "Dado y firmada en la Asamblea Nacional Constituyente"), "last": None,
     "from": "2020-02-19", "gazette": ("6.507 Extraordinario", "29 Jan 2020"),
     "law": ("decreto-constituyente-loa-2020", law("Decreto Constituyente de Reforma de la Ley Orgánica de Aduanas (2020)", "Decreto Constituyente de Reforma del Decreto con Rango, Valor y Fuerza de Ley Orgánica de Aduanas, de la Asamblea Nacional Constituyente, de 29 de enero de 2020", "decree", "2020-01-29", "2020-01-29", GACETA + "storage/2020/T028700032247-0-GOE_6.507-000.pdf")),
     "first_law": None, "earlier": [],
     "contents": "Decreto Constituyente de Reforma of the Ley Orgánica de Aduanas (art. 21 orders the reprint) followed by the texto único of the law.",
     "note": "Texto único of the Ley Orgánica de Aduanas as reformed by Decreto Constituyente of 29 Jan 2020 (G.O. 6.507 Ext.), in force once twenty continuous days have run from the day after publication (art. 195 as worded by the reform), that is from 2020-02-19. Earlier texts (2014) are image scans and are not in this record.",
     "decisions": ["LOA: the Decreto Constituyente de Reforma of 29 Jan 2020 (arts. 1-21) is printed in G.O. 6.507 Ext., followed by the law in full (its art. 21 orders a single text); only the texto único is read. In force 'cumplido el plazo de veinte (20) días continuos, contado a partir del día siguiente de su publicación' (art. 195 as reformed): the twenty days run from 30 Jan to 18 Feb 2020, so the first day in force is taken as 2020-02-19. Credited to the publisher as the oldest version available."]},
]

UNKNOWN = "[La fuente no da el texto vigente en esta fecha.]\n"


def ve2_acts() -> list[dict]:
    """Acts added in the second deepening pass (gitlaw-VE-2, 2026-10-29): parts 38-44."""
    def gz(path):
        return GACETA + "storage/" + path
    CORR = gz("2022/T028700038641-0-6.699_02-05-2022-000.pdf")
    MUJ = gz("2021/T028700037619-0-GOE_6.667-000.pdf")
    DP = gz("2022/T028700038949-0-6.702_25-05-2022_cc-000.pdf")
    IGTF = gz("2022/T028700038065-0-6.687_25-02-2022-000.pdf")
    ZEE = gz("2022/T028700039556-0-GOE_6.710-000.pdf")
    LOED = gz("2023/T028700042208-0-GOE_6.745_ma-000.pdf")
    LOH = gz("2026/6978-2026-01-29-EXTRAORDINARIA.pdf")
    DADA = "Dada, firmada y sellada en el Palacio Federal Legislativo"
    acts = [
        {"part": "38-corrupcion", "slug": "ley-contra-la-corrupcion", "short": "LCC", "title": "Ley contra la Corrupción",
         "url": CORR, "cut": ("LEY CONTRA LA CORRUPCIÓN", DADA), "last": None,
         "from": "2022-05-02", "gazette": ("6.699 Extraordinario", "2 May 2022"),
         "law": ("ley-reforma-corrupcion-2022", law("Ley de Reforma de la Ley contra la Corrupción (2022)", "Ley de Reforma del Decreto con Rango, Valor y Fuerza de Ley contra la Corrupción, sancionada el 31 de marzo de 2022", "law", "2022-03-31", "2022-05-02", CORR)),
         "first_law": None, "earlier": [],
         "contents": "Ley de Reforma del Decreto con Rango, Valor y Fuerza de Ley contra la Corrupción (art. 28 orders the reprint) followed by the texto único of the Ley contra la Corrupción.",
         "note": "Texto único of the Ley contra la Corrupción as reformed by the Ley de Reforma sanctioned on 31 Mar 2022, printed in G.O. 6.699 Ext. of 2 May 2022 and in force on publication (art. 27 of the reform). Earlier texts (2003, 2014) are image scans and are not in this record.",
         "decisions": ["LCC: the Ley de Reforma del Decreto con Rango, Valor y Fuerza de Ley contra la Corrupción (arts. 1-28) is printed first in G.O. 6.699 Ext. of 2 May 2022, then the law in full (its art. 28 orders the single text); only the texto único is read, from its title to the closing 'Dada, firmada y sellada'. In force 'a partir de su publicación' (art. 27 of the reform), so from 2022-05-02. Credited to the publisher as the oldest version available."]},
        {"part": "39-mujeres", "slug": "ley-organica-sobre-el-derecho-de-las-mujeres-a-una-vida-libre-de-violencia", "short": "LODMVLV",
         "title": "Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia",
         "url": MUJ, "cut": ("A UNA VIDA LIBRE DE VIOLENCIA", DADA), "last": None, "single": (39, 40, 41),
         "skip": [(35, 1, "Inicio ante otro órgano receptor"), (38, 0, "2. Una sala de trabajo")], "furniture": r"Pá i \d+ d 139|á d",
         "restore": [(19, 0, "ocasionar condiciones de violencia", 2)],
         "from": "2021-12-16", "gazette": ("6.667 Extraordinario", "16 Dec 2021"),
         "law": ("lo-reforma-mujeres-2021", law("Ley Orgánica de Reforma de la Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia (2021)", "Ley Orgánica de Reforma a la Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia, sancionada el 1 de diciembre de 2021", "law", "2021-12-01", "2021-12-16", MUJ)),
         "first_law": None, "earlier": [],
         "contents": "Ley Orgánica de Reforma a la Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia (art. 66 orders the reprint) followed by the texto único of the law.",
         "note": "Texto único of the Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia as reformed in 2021, printed in G.O. 6.667 Ext. of 16 Dec 2021 and in force on publication (art. 65 of the reform; Disposición final única). The laws of 2007 and 2014 are not in this record.",
         "decisions": ["LODMVLV: the Ley Orgánica de Reforma of 2021 (arts. 1-66) is printed first in G.O. 6.667 Ext., then the law in full (art. 66 orders the single text); only the texto único is read, from its title to the closing 'Dada, firmada y sellada'. In force 'a partir de su publicación' (art. 65 of the reform and the Disposición final única of the text), so from 2021-12-16. Credited to the publisher as the oldest version available. Its last three pages (39-41, the dispositions) are set in one full-width column and are read as such."]},
        {"part": "40-defensa-publica", "slug": "ley-organica-de-la-defensa-publica", "short": "LODP", "title": "Ley Orgánica de la Defensa Pública",
         "url": DP, "cut": ("LEY ORGÁNICA DE LA DEFENSA PÚBLICA", DADA), "last": None, "furniture": r"Pá i \d+ d 83",
         "from": "2022-05-25", "gazette": ("6.702 Extraordinario", "25 May 2022"),
         "law": ("lo-reforma-defensa-publica-2022", law("Ley Orgánica de Reforma Parcial de la Ley Orgánica de la Defensa Pública (2022)", "Ley Orgánica de Reforma Parcial de la Ley Orgánica de la Defensa Pública, sancionada el 17 de mayo de 2022", "law", "2022-05-17", "2022-05-25", DP)),
         "first_law": None, "earlier": [],
         "contents": "Ley Orgánica de Reforma Parcial de la Ley Orgánica de la Defensa Pública followed by the texto único of the law.",
         "note": "Texto único of the Ley Orgánica de la Defensa Pública as reformed in 2022, printed in G.O. 6.702 Ext. of 25 May 2022 and in force on publication (Disposición final única). Earlier texts are not in this record.",
         "decisions": ["LODP: the Ley Orgánica de Reforma Parcial of 2022 is printed first in G.O. 6.702 Ext., then the law in full; only the texto único is read, from its title to the closing 'Dada, firmada y sellada'. In force 'a partir de su publicación' (Disposición final única), so from 2022-05-25. Credited to the publisher as the oldest version available."]},
        {"part": "41-igtf", "slug": "ley-de-impuesto-a-las-grandes-transacciones-financieras", "short": "LIGTF",
         "title": "Ley de Impuesto a las Grandes Transacciones Financieras",
         "url": IGTF, "cut": ("FINANCIERAS", DADA), "last": None,
         "from": "2022-03-27", "gazette": ("6.687 Extraordinario", "25 Feb 2022"),
         "law": ("ley-reforma-igtf-2022", law("Ley de Reforma Parcial de la Ley de Impuesto a las Grandes Transacciones Financieras (2022)", "Ley de Reforma Parcial del Decreto con Rango, Valor y Fuerza de Ley de Impuesto a las Grandes Transacciones Financieras, sancionada el 3 de febrero de 2022", "law", "2022-02-03", "2022-02-25", IGTF)),
         "first_law": None, "earlier": [],
         "contents": "Ley de Reforma Parcial del Decreto con Rango, Valor y Fuerza de Ley de Impuesto a las Grandes Transacciones Financieras (art. 13 orders the reprint) followed by the texto único of the law.",
         "note": "Texto único of the Ley de Impuesto a las Grandes Transacciones Financieras as reformed in 2022, printed in G.O. 6.687 Ext. of 25 Feb 2022 and in force thirty continuous days after publication (art. 25), that is from 27 Mar 2022. Earlier texts (2015, 2018) are not in this record.",
         "decisions": ["LIGTF: the Ley de Reforma Parcial of 2022 (arts. 1-13) is printed first in G.O. 6.687 Ext. of 25 Feb 2022, then the law in full (art. 13 orders the single text); only the texto único is read, from the second line of its title ('FINANCIERAS') to the closing 'Dada, firmada y sellada'. Art. 25 (added by the reform): in force 'a los treinta (30) días continuos siguientes a su publicación'; the thirtieth day after 25 Feb 2022 is 27 Mar 2022, counted as for the COT, so the version is dated 2022-03-27 (the Asamblea Nacional's law page gives 28/03/2022 as vigencia; the law's own clause is followed). Credited to the publisher as the oldest version available."]},
        {"part": "42-zee", "slug": "ley-organica-de-las-zonas-economicas-especiales", "short": "LOZEE",
         "title": "Ley Orgánica de las Zonas Económicas Especiales",
         "url": ZEE, "cut": ("LEY ORGÁNICA DE LAS ZONAS ECONÓMICAS ESPECIALES", DADA), "last": None,
         "flush_sections": True, "furniture": r"p|0 de julio de 2022 N° 6\.710 Extraordinario",
         "from": "2022-07-20", "gazette": ("6.710 Extraordinario", "20 Jul 2022"),
         "law": ("ley-organica-zee-2022", law("Ley Orgánica de las Zonas Económicas Especiales (2022)", "Ley Orgánica de las Zonas Económicas Especiales, sancionada el 30 de junio de 2022", "law", "2022-06-30", "2022-07-20", ZEE)),
         "first_law": "ley-organica-zee-2022", "earlier": [],
         "contents": "Ley Orgánica de las Zonas Económicas Especiales, as enacted.",
         "note": "The Ley Orgánica de las Zonas Económicas Especiales as enacted, G.O. 6.710 Ext. of 20 Jul 2022, in force on publication.",
         "decisions": ["LOZEE: a new law, printed once in G.O. 6.710 Ext. of 20 Jul 2022; read from its title to the closing 'Dada, firmada y sellada'. In force on publication, 2022-07-20 (its final disposition). Credited to the law itself as first_law (the act as enacted)."]},
        {"part": "43-extincion-dominio", "slug": "ley-organica-de-extincion-de-dominio", "short": "LOED", "title": "Ley Orgánica de Extinción de Dominio",
         "url": LOED, "cut": ("LEY ORGÁNICA DE EXTINCIÓN DE DOMINIO", DADA), "last": None, "single": (7, 8),
         "furniture": r"8 de abril de 2023 N° 6\.745 Extraordinario",
         "from": "2023-04-28", "gazette": ("6.745 Extraordinario", "28 Apr 2023"),
         "law": ("ley-organica-extincion-dominio-2023", law("Ley Orgánica de Extinción de Dominio (2023)", "Ley Orgánica de Extinción de Dominio, sancionada el 27 de abril de 2023", "law", "2023-04-27", "2023-04-28", LOED)),
         "first_law": "ley-organica-extincion-dominio-2023", "earlier": [],
         "contents": "Ley Orgánica de Extinción de Dominio, as enacted.",
         "note": "The Ley Orgánica de Extinción de Dominio as enacted, G.O. 6.745 Ext. of 28 Apr 2023, in force on publication (Disposición final única).",
         "decisions": ["LOED: a new law, printed once in G.O. 6.745 Ext. of 28 Apr 2023; read from its title to the closing 'Dada, firmada y sellada'. In force 'a partir de su publicación' (Disposición final única), so from 2023-04-28. Credited to the law itself as first_law. Its last two pages (7-8, the dispositions) are set in one full-width column and are read as such."]},
        {"part": "44-hidrocarburos", "slug": "ley-organica-de-hidrocarburos", "short": "LOH", "title": "Ley Orgánica de Hidrocarburos",
         "url": LOH, "cut": ("LEY ORGÁNICA DE HIDROCARBUROS", "Dado, firmado y sellado en el Palacio Federal Legislativo"), "last": None,
         "from": "2026-01-29", "gazette": ("6.978 Extraordinario", "29 Jan 2026"),
         "law": ("ley-reforma-loh-2026", law("Ley de Reforma de la Ley Orgánica de Hidrocarburos (2026)", "Ley de Reforma de la Ley Orgánica de Hidrocarburos, sancionada el 29 de enero de 2026", "law", "2026-01-29", "2026-01-29", LOH)),
         "first_law": None, "earlier": [],
         "deferred": {"from": "2026-03-31",
                      "units": {"art-051": "reworded", "art-055": "reworded", "art-056": "new", "art-057": "new", "art-058": "new", "art-059": "new"},
                      "note": "Arts. 51 and 55-59 as printed in the texto único of G.O. 6.978 Ext. take effect once sixty continuous days following publication have run (Disposición final única): from 31 Mar 2026."},
         "contents": "Ley de Reforma de la Ley Orgánica de Hidrocarburos (art. 35 orders the reprint) followed by the texto único of the law.",
         "note": "Texto único of the Ley Orgánica de Hidrocarburos as reformed in 2026, printed in G.O. 6.978 Ext. of 29 Jan 2026 and in force on publication except arts. 51 and 55-59 (Disposición final única), which take effect on 31 Mar 2026: until then arts. 56-59 (inserted by the reform) are absent and arts. 51 and 55 (reworded by it) read '[La fuente no da el texto vigente en esta fecha.]', because their earlier wording (2006) survives only as an image scan.",
         "decisions": ["LOH: the Ley de Reforma de la Ley Orgánica de Hidrocarburos (arts. 1-35) is printed first in G.O. 6.978 Ext. of 29 Jan 2026, then the law in full (art. 35 orders the single text); only the texto único is read, from its title to the closing 'Dado, firmado y sellado'. Its Disposición final única: in force on publication 'salvo los artículos 51, 55, 56, 57, 58 y 59, los cuales entrarán en vigencia una vez transcurrido sesenta (60) días continuos siguientes a su publicación'. The sixty days following 29 Jan 2026 run from 30 Jan to 30 Mar 2026, so those articles take effect on 2026-03-31 (counted as for the Ley Orgánica de Aduanas). The rest is dated 2026-01-29 and credited to the publisher as the oldest version available.",
                       "LOH arts. 51 and 55-59 (coordinator rule for text that appears before it is in force): per the reform's own articles 16-21, arts. 56, 57, 58 and 59 are new (inserted by the reform), so they are absent from the version of 2026-01-29; arts. 51 and 55 replace former arts. 44 and 48, whose wording is not in any text-layer source, so in that version they read '[La fuente no da el texto vigente en esta fecha.]'. The printed wording of all six arrives on 2026-03-31, credited to the Ley de Reforma of 2026."]},
    ]
    for s in acts:
        s["right_epigraphs"] = True  # long or wrapped epigraphs set flush right (see right_epigraph_lines)
    return acts


ACTS += ve2_acts()


COMMON_DECISIONS = [
    "Codes and laws from born-digital gazettes (corpus.d/31-... parts, one per act): only gazettes with a born-digital text layer are used. The Gaceta Oficial portal (gacetaoficial.gob.ve) indexes 2010 on, but its issues before about 2018, and every TSJ or Asamblea Nacional copy of older codes tried (Código Civil 1982, Código Penal 2005, Código de Comercio 1955, COPP 2012, COT 2014, LOTSJ 2010), are image scans; with no OCR they are not read, so each act starts at its latest full official printing.",
    "Gazette text extraction (gazette_text.py): these gazettes are made of text frames pasted on white boxes, and their text layer also holds words that are never printed: frame overflow cut off by a clip path (repeated at the top or bottom of the next page) and older text painted over by a later white box. pdftotext prints all of it (for example item 8 of COPP art. 111 twice). Only characters the page paints are kept, decided from the PDF's own drawing instructions (MuPDF clip handling, and the drawing order of text versus white fills); spaces come from the gaps between printed glyphs. No page image is rendered or recognised. Tool: " + gazette_text.version() + ".",
    "Paragraphs are rebuilt from the printed lines: a line that ends with . : ; well short of the right margin ends a paragraph; articles, numbered items and ordinal dispositions start their own; a centred line is a heading; a short line set flush right is the article's epigraph, kept as the first line of the article's file. Headings, in order, are in titulos.md. Spellings are kept as printed; the only typesetting changes are a space after 'Artículo N.' where the gazette prints none, and 'A rtículo' (a kerned capital read as a separate glyph, LOA art. 55) joined to 'Artículo'.",
    "Checks (parse_codes.py --verify): for each act the words of its files equal, as a multiset, the words printed in its part of the gazette; every word the extraction dropped from the text layer is listed, and each dropped run was confirmed to be printed elsewhere in the act (frame overflow) or to be a fragment of the running header. Each article number from 1 to the last occurs exactly once (plus lettered inserts such as COPP art. 126-A), and numbered items run in sequence.",
    "No later reform of these acts was found: the Asamblea Nacional's list of sanctioned laws (Wayback CDX of asambleanacional.gob.ve/leyes/, captures to 2026-01) names no reform after the gazettes used here.",
]


def build_act(spec: dict) -> tuple[dict, dict]:
    units = units_from(paragraphs(act_columns(spec), spec.get("flush_sections", False),
                                  spec.get("right_epigraphs", False)), spec["short"])
    nums = [int(k[4:7]) for k in units if k.startswith("art-") and len(k) == 7]
    problems = check_sequence(units, spec["short"], spec["last"] or max(nums))
    if problems:
        raise SystemExit("\n".join(problems))
    key, lw = spec["law"]
    laws = {key: lw}
    for k, label, gazette, day, kind in spec["earlier"]:
        laws[k] = law(label, f"{label}, publicado en la Gaceta Oficial N° {gazette} de {day}", kind, day, day, spec["url"])
    full = finish(units)
    versions = [{"from": spec["from"], "source_url": spec["url"], "sha256": sha_of(spec["url"]),
                 "units": full, "credits": {}, "note": spec["note"]}]
    if spec.get("deferred"):
        # provisions whose printed wording takes effect later than the rest (the law's own vigencia
        # clause): before that day a provision the reform inserted is absent, and one it reworded
        # reads as unknown (the earlier wording is not in any text-layer source); the printed wording
        # arrives on its own day, credited to the reform
        d = spec["deferred"]
        first = dict(full)
        for k, how in d["units"].items():
            if how == "new":
                del first[k]
            else:
                first[k] = {"label": full[k]["label"], "kind": full[k]["kind"], "text": UNKNOWN}
        versions = [dict(versions[0], units=first),
                    {"from": d["from"], "source_url": spec["url"], "sha256": sha_of(spec["url"]),
                     "changes": {k: full[k] for k in d["units"]}, "credits": {k: [key] for k in d["units"]},
                     "note": d["note"]}]
    act = {"slug": spec["slug"], "short": spec["short"], "title": spec["title"], "url": spec["url"],
           "first_law": spec["first_law"], "earlier_laws": [e[0] for e in spec["earlier"]],
           "versions": versions}
    part = {"laws": laws, "acts": [act], "sources": [gazette_source(*spec["gazette"], spec["url"], spec["contents"])],
            "decisions": spec["decisions"], "ai_use": []}
    return part, units


def build() -> dict[str, dict]:
    parts = {"30-gaceta-digital": {"acts": [], "decisions": COMMON_DECISIONS,
                                   "ai_use": ["none: no model wrote, summarised or corrected any legal text in the gazette parts; parsing is rule-based (parse_codes.py, gazette_text.py)."]}}
    for spec in ACTS:
        parts[spec["part"]], _ = build_act(spec)
    return parts


def main() -> None:
    out = OUT
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    specs = [s for s in ACTS if not only or s["short"] in only]
    if "--verify" in sys.argv or "--check" in sys.argv:
        for spec in specs:
            part, units = build_act(spec)
            if "--verify" in sys.argv:
                for line in verify(spec, units):
                    print(spec["short"], line)
            for p in items_check(units):
                print(spec["short"], "ITEMS", p)
    parts = build()
    out.mkdir(exist_ok=True)
    for name, part in parts.items():
        tmp = out / (name + ".json.tmp")
        tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(out / (name + ".json"))
        for a in part["acts"]:
            print("wrote", name, a["slug"], "units:", len(a["versions"][-1]["units"]))


if __name__ == "__main__":
    main()
