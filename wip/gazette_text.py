"""Visible text of a born-digital Gaceta Oficial PDF (two columns), read from its text layer.

Gazettes from about 2018 on are typeset by pasting text frames on white boxes. Their text layer
also holds words that are never printed: frame overflow cut off by the frame's clip path, and
older text later covered by an opaque white box. pdftotext prints both. This module keeps only
the characters the page actually paints, decided from the PDF's own drawing instructions:

- a character outside its clip path is dropped (MuPDF text extraction with the clip flag), and
- a character whose centre lies inside a white filled shape drawn after it is dropped
  (PyMuPDF texttrace sequence numbers versus the page's filled paths).

No page image is rendered and nothing is recognised from pixels (no OCR). Deterministic for a
given PyMuPDF/MuPDF version, which corpus decisions record.

    visible_columns(path) -> [Column(page, side, left, right, lines=[Line(x0, x1, y, text, size)])]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

HEADER = "GACETA OFICIAL DE LA REPÚBLICA BOLIVARIANA DE VENEZUELA"


@dataclass
class Line:
    x0: float
    x1: float
    y: float
    text: str
    size: float


@dataclass
class Column:
    page: int
    side: int  # 0 left, 1 right
    left: float = 0.0
    right: float = 0.0
    lines: list[Line] = field(default_factory=list)


def version() -> str:
    return f"PyMuPDF {fitz.VersionBind} (MuPDF {fitz.VersionFitz})"


def _key(c: str, x: float, y: float) -> tuple:
    return (c, round(x, 1), round(y, 1))


def hidden_chars(pg, unmask_cut_lines: bool = False) -> set:
    """Characters painted over by a later opaque white fill, or drawn invisibly.

    unmask_cut_lines (opt-in, per act): a white box laid over a line that the page otherwise prints
    (same text run, same baseline, some of its letters painted) does not hide the rest of that line.
    Used where boxes meant to hide the source document's page numbers also cover the ends of lines."""
    fills = []
    for d in pg.get_drawings():
        f = d.get("fill")
        if f is not None and min(f[:3]) > 0.95 and (d.get("fill_opacity") or 1) > 0.5:
            fills.append((d["seqno"], fitz.Rect(d["rect"])))
    out = set()
    for sp in pg.get_texttrace():
        invisible = sp["type"] == 3 or sp["opacity"] == 0
        later = [r for sq, r in fills if sq > sp["seqno"]]
        if not invisible and not later:
            continue
        hid, shown = [], set()
        for ch in sp["chars"]:
            o, bb = ch[2], ch[3]
            p = fitz.Point((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
            if invisible or any(p in r for r in later):
                hid.append((_key(chr(ch[0]), o[0], o[1]), round(o[1], 1)))
            elif chr(ch[0]).strip():
                shown.add(round(o[1], 1))
        for k, y in hid:
            if not (unmask_cut_lines and not invisible and y in shown):
                out.add(k)
    return out


def page_chars(pg, filtered: bool = True, unmask_cut_lines: bool = False) -> list[tuple]:
    """Visible characters: (baseline y, x0, x1, char, size). filtered=False keeps every character
    of the text layer (for the cross-check of what was dropped)."""
    hid = hidden_chars(pg, unmask_cut_lines) if filtered else set()
    flags = fitz.TEXTFLAGS_TEXT if filtered else fitz.TEXTFLAGS_TEXT & ~fitz.TEXT_MEDIABOX_CLIP
    out = []
    for b in pg.get_text("rawdict", flags=flags)["blocks"]:  # TEXTFLAGS_TEXT includes the clip flag
        for l in b.get("lines", []):
            if abs(l["dir"][1]) > 0.01:
                continue  # rotated text (margin notes)
            for sp in l["spans"]:
                for ch in sp["chars"]:
                    x, y = ch["origin"]
                    if _key(ch["c"], x, y) in hid:
                        continue
                    out.append((y, ch["bbox"][0], ch["bbox"][2], ch["c"], sp["size"]))
    return out


def _lines(chars: list[tuple]) -> list[Line]:
    chars = sorted(chars, key=lambda c: (round(c[0], 1), c[1]))
    rows: list[list[tuple]] = []
    for c in chars:
        if rows and abs(rows[-1][0][0] - c[0]) <= 1.5:
            rows[-1].append(c)
        else:
            rows.append([c])
    out = []
    for row in rows:
        row.sort(key=lambda c: c[1])
        text = ""
        last_x1 = None
        x0 = x1 = None
        for y, a, b, ch, size in row:
            if ch.strip():
                if last_x1 is not None and a - last_x1 > 0.18 * size and not text.endswith(" "):
                    text += " "
                text += ch
                last_x1 = b
                x0 = a if x0 is None else x0
                x1 = b
            else:
                if text and not text.endswith(" "):
                    text += " "
        if text.strip():
            out.append(Line(x0, x1, row[0][0], text.strip(), max(c[4] for c in row)))
    return out


def visible_columns(path: Path | str, pages: range | None = None, filtered: bool = True,
                    single: frozenset[int] | set[int] = frozenset(),
                    unmask: frozenset[int] | set[int] = frozenset()) -> list[Column]:
    """`single`: page numbers (1-based) set in one full-width column (some acts end with their
    dispositions set this way); each is read as one column, side 0. `unmask`: page numbers whose
    lines cut short by a white box are read whole (hidden_chars, unmask_cut_lines)."""
    doc = fitz.open(str(path))
    cols: list[Column] = []
    for pno in (pages or range(len(doc))):
        pg = doc[pno]
        mid = pg.rect.width / 2
        chars = page_chars(pg, filtered)
        # running header: the line that holds the gazette's name near the top
        top = [l for l in _lines([c for c in chars if c[0] < 80])]
        drop = [l.y for l in top if HEADER in l.text.replace("  ", " ")]
        if drop:
            chars = [c for c in chars if c[0] > drop[0] + 4]
        if pno + 1 in single:
            ls = _lines(chars)
            if ls:
                cols.append(Column(pno + 1, 0, min(l.x0 for l in ls), max(l.x1 for l in ls), ls))
            continue
        for side in (0, 1):
            cc = [c for c in chars if (c[1] < mid) == (side == 0)]
            ls = _lines(cc)
            if not ls:
                continue
            col = Column(pno + 1, side, min(l.x0 for l in ls), max(l.x1 for l in ls), ls)
            cols.append(col)
    return cols


def dump(path: Path | str) -> str:
    """Plain dump for inspection: one line per printed line, with its offsets."""
    out = []
    for c in visible_columns(path):
        out.append(f"=== page {c.page} col {c.side} [{c.left:.0f}-{c.right:.0f}]")
        for l in c.lines:
            out.append(f"{l.x0 - c.left:6.1f} {c.right - l.x1:6.1f} | {l.text}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(dump(sys.argv[1]), end="")
