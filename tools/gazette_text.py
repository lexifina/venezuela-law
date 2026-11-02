"""Visible text of a born-digital Gaceta Oficial PDF (two columns), read from its text layer.

Gazettes from about 2018 on are typeset by pasting text frames on white boxes. Their text layer
also holds words that are never printed: frame overflow cut off by the frame's clip path, and
older text later covered by an opaque white box. pdftotext prints both. This module keeps only
the characters the page actually paints, decided from the PDF's own drawing instructions:

- a character outside its clip path is dropped (MuPDF text extraction with the clip flag), and
- a character whose centre lies inside a white filled shape drawn after it is dropped
  (PyMuPDF texttrace sequence numbers versus the page's filled paths).

A lone fragment that a clip cuts to a sliver (the descenders of an overflow line) is dropped per
act (parse_codes spec 'drop'), each checked with sliver_line().

A glyph whose /ToUnicode entry is a space although the font draws a letter is read from the
embedded font program's own Unicode cmap (unmapped_glyphs).

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


def _white_fills(pg, fill_clips: bool = True) -> list:
    """Opaque white filled shapes: [(seqno, rect)]. fill_clips (the default since 2026-11-02): each fill is
    cut to the clip paths in force when it is drawn, and a fill its clips leave nothing of paints nothing and
    hides nothing (LODGE, G.O. 6.798 Ext.: white boxes drawn inside a frame's clip far below them; LEFPI and
    LOH epigraphs). fill_clips=False takes each fill's whole rectangle (earlier builds)."""
    white = lambda d: d.get("fill") is not None and min(d["fill"][:3]) > 0.95 and (d.get("fill_opacity") or 1) > 0.5
    if not fill_clips:
        return [(d["seqno"], fitz.Rect(d["rect"])) for d in pg.get_drawings() if white(d)]
    out, stack = [], []  # stack: (level, clip rect) of the clips in force
    for d in pg.get_drawings(extended=True):
        lv = d.get("level", 0)
        while stack and stack[-1][0] >= lv:
            stack.pop()
        if d.get("type") == "clip":
            stack.append((lv, fitz.Rect(d["scissor"])))
        elif d.get("type") != "group" and white(d):
            r = fitz.Rect(d["rect"])
            x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1
            for _, c in stack:
                x0, y0, x1, y1 = max(x0, c.x0), max(y0, c.y0), min(x1, c.x1), min(y1, c.y1)
            if x1 > x0 and y1 > y0:
                out.append((d["seqno"], fitz.Rect(x0, y0, x1, y1)))
    return out


def hidden_chars(pg, unmask_cut_lines: bool = False, any_run: bool = False, fill_clips: bool = True) -> set:
    """Characters painted over by a later opaque white fill, or drawn invisibly.

    unmask_cut_lines (opt-in, per act): a white box laid over a line that the page otherwise prints
    (same text run, same baseline, some of its letters painted) does not hide the rest of that line.
    Used where boxes meant to hide the source document's page numbers also cover the ends of lines.
    any_run (opt-in, with unmask_cut_lines): the line's painted letters may belong to another text run
    on the same baseline in the same column (LEFPI: 'segurid' + 'ad ciudadana, en')."""
    fills = _white_fills(pg, fill_clips)
    out = set()
    mid = pg.rect.width / 2
    painted = set()  # (column, baseline) with at least one painted letter, over all runs
    if any_run:
        for sp in pg.get_texttrace():
            if sp["type"] == 3 or sp["opacity"] == 0:
                continue
            later = [r for sq, r in fills if sq > sp["seqno"]]
            for ch in sp["chars"]:
                bb = ch[3]
                pt = fitz.Point((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
                if chr(ch[0]).strip() and not any(pt in r for r in later):
                    painted.add((ch[2][0] < mid, round(ch[2][1], 1)))
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
                hid.append((_key(chr(ch[0]), o[0], o[1]), round(o[1], 1), o[0] < mid))
            elif chr(ch[0]).strip():
                shown.add(round(o[1], 1))
        for k, y, side in hid:
            if not (unmask_cut_lines and not invisible and (y in shown or (side, y) in painted)):
                out.add(k)
    return out


def _font_unicode(pg) -> dict:
    """{font name as the text trace gives it: {glyph id: character}} from each embedded TrueType font
    program's own Unicode cmap, the table the renderer uses to pick the glyph for a WinAnsi code."""
    out: dict[str, dict] = {}
    for xref, ext, typ, base, *_ in pg.get_fonts():
        if typ != "TrueType" or ext != "ttf":
            continue
        try:
            f = fitz.Font(fontbuffer=pg.parent.extract_font(xref)[3])
        except Exception:
            continue
        m = {}
        for u in f.valid_codepoints():
            g = f.has_glyph(u)
            if g and (g not in m or chr(u) == " "):
                m[g] = " " if chr(u) == "\xa0" and g not in m else chr(u)
        name = base.split("+", 1)[-1]
        if name in out and out[name] != m:
            out[name] = None  # two different programs under one name: do not guess
        else:
            out.setdefault(name, m)
    return out


def unmapped_glyphs(pg) -> dict:
    """{(x, y): character} for glyphs whose /ToUnicode entry says U+0020 although the font draws a
    letter there (a broken ToUnicode CMap: LOED, G.O. 6.745 Ext., maps 21 letter codes of one embedded
    Arial to a space). The character is read from the font program's own Unicode cmap for that glyph."""
    fonts = None
    out = {}
    for sp in pg.get_texttrace():
        for ch in sp["chars"]:
            if ch[0] != 32:
                continue
            if fonts is None:
                fonts = _font_unicode(pg)
            m = fonts.get(sp["font"])
            c = m.get(ch[1]) if m else None
            if c and c != " ":
                out[(round(ch[2][0], 1), round(ch[2][1], 1))] = c
    return out


def sliver_line(pg, y: float, x0: float, x1: float) -> bool:
    """True when every glyph printed on the baseline y between x0 and x1 is cut to a sliver by a clip
    rectangle: the clip's top or bottom edge crosses the glyph's box and less than half of the box's
    height lies inside it (the descenders of an overflow line whose body sits above a text frame's
    top edge). MuPDF's clip handling keeps any glyph that touches its clip; the printed page shows
    only a stroke of it. Used to check each spec 'drop' of a fragment, not to drop anything itself."""
    scis = [fitz.Rect(d["scissor"]) for d in pg.get_drawings(extended=True) if d["type"] == "clip" and d.get("scissor")]
    boxes = [ch["bbox"] for b in pg.get_text("rawdict", flags=fitz.TEXTFLAGS_TEXT)["blocks"] for l in b.get("lines", [])
             for sp in l["spans"] for ch in sp["chars"]
             if ch["c"].strip() and abs(ch["origin"][1] - y) < 0.2 and x0 - 0.5 <= ch["bbox"][0] and ch["bbox"][2] <= x1 + 0.5]
    if not boxes:
        return False
    for bx0, by0, bx1, by1 in boxes:
        h = by1 - by0
        if not any(r.x0 - 0.5 <= bx0 and bx1 <= r.x1 + 0.5 and (by0 < r.y0 < by1 or by0 < r.y1 < by1)
                   and min(by1, r.y1) - max(by0, r.y0) < 0.5 * h for r in scis):
            return False
    return True


def page_chars(pg, filtered: bool = True, unmask_cut_lines: bool = False, any_run: bool = False,
               same_spot_once: bool = False, fill_clips: bool = True, overpaint_once: bool = False) -> list[tuple]:
    """Visible characters: (baseline y, x0, x1, char, size). filtered=False keeps every character
    of the text layer (for the cross-check of what was dropped). Glyphs whose ToUnicode entry is
    broken are read from their font's own cmap in both modes (unmapped_glyphs).
    same_spot_once (opt-in, both modes): a character drawn again at the same spot (same character,
    origin within 0.3 pt) prints one mark and is read once (a gazette whose whole text layer is
    drawn two or three times over itself, G.O. 6.872 Ext.).
    overpaint_once (opt-in, filtered mode only): a character drawn later on the same baseline over a character
    already read, their boxes covering each other for at least 80% of the narrower one's width, paints over that
    mark and is read once, as the earlier character (patch glyphs set over a heading, G.O. 6.686 Ext. p. 10:
    'servidor' + 'res' over 'servidoras', and a patch glyph mapped 'F' in the text layer over a 'c')."""
    hid = hidden_chars(pg, unmask_cut_lines, any_run, fill_clips) if filtered else set()
    flags = fitz.TEXTFLAGS_TEXT if filtered else fitz.TEXTFLAGS_TEXT & ~fitz.TEXT_MEDIABOX_CLIP
    fix = unmapped_glyphs(pg)
    out = []
    seen: dict = {}
    for b in pg.get_text("rawdict", flags=flags)["blocks"]:  # TEXTFLAGS_TEXT includes the clip flag
        for l in b.get("lines", []):
            if abs(l["dir"][1]) > 0.01:
                continue  # rotated text (margin notes)
            for sp in l["spans"]:
                for ch in sp["chars"]:
                    x, y = ch["origin"]
                    if _key(ch["c"], x, y) in hid:
                        continue
                    c = fix.get((round(x, 1), round(y, 1)), ch["c"]) if ch["c"] == " " else ch["c"]
                    if same_spot_once:
                        near = seen.setdefault((c, round(y)), [])
                        if any(abs(x - a) < 0.3 and abs(y - b) < 0.3
                               for k in {(c, round(y - 0.3)), (c, round(y + 0.3)), (c, round(y))} for a, b in seen.get(k, ())):
                            continue
                        near.append((x, y))
                    if overpaint_once and filtered:
                        x0, x1 = ch["bbox"][0], ch["bbox"][2]
                        if any(abs(y - o[0]) < 0.5 and o[3] != " " and c != " " and
                               min(x1, o[2]) - max(x0, o[1]) >= 0.8 * min(x1 - x0, o[2] - o[1]) for o in out):
                            continue
                    out.append((y, ch["bbox"][0], ch["bbox"][2], c, sp["size"]))
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
                    unmask: frozenset[int] | set[int] = frozenset(), unmask_runs: bool = False,
                    same_spot_once: bool = False, fill_clips: bool = True,
                    overpaint: frozenset[int] | set[int] = frozenset()) -> list[Column]:
    """`single`: page numbers (1-based) set in one full-width column (some acts end with their
    dispositions set this way); each is read as one column, side 0. `unmask`: page numbers whose
    lines cut short by a white box are read whole (hidden_chars, unmask_cut_lines)."""
    doc = fitz.open(str(path))
    cols: list[Column] = []
    for pno in (pages or range(len(doc))):
        pg = doc[pno]
        mid = pg.rect.width / 2
        chars = page_chars(pg, filtered, pno + 1 in unmask, unmask_runs, same_spot_once, fill_clips, pno + 1 in overpaint)  # overpaint: pages (opt-in, G.O. 6.686 Ext.)
        # running header: the line that holds the gazette's name near the top, or the start of it where the
        # page paints only part of the header's text layer (G.O. 6.714 Ext. p. 2: 'GACETA OFICIAL DE LA REPÚBLICA BOLI'
        # and a lone 'V' on the same baseline; the rest of the printed header is not in the visible text layer)
        top = [l for l in _lines([c for c in chars if c[0] < 80])]
        drop = [l.y for l in top if HEADER in l.text.replace("  ", " ") or HEADER[:24] in l.text]
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
