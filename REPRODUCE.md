# How this repository was made (Venezuela)

This file is written by the build on 2026-10-28, the day the source data was retrieved. Everything below is enough to rebuild this repository hash for hash.

## Sources

| Source | Address | Retrieved | Requests | Licence |
| --- | --- | --- | ---: | --- |
| Gaceta Oficial N° 5.908 Extraordinario (19 Feb 2009), copy hosted by the Instituto Nacional de Estadística | <https://ine.gob.ve/wp-content/uploads/2024/08/1-ConstitucionVzla_GacetaOficial_5908.pdf> | 2026-10-28 | 1 | Official act of the State; Ley sobre el Derecho de Autor art. 11 is understood to exclude official acts from protection (not checked against the gazette here). |
| Tribunal Supremo de Justicia, constitucion1999.htm (TSJ transcription of G.O. 5.453 Ext., 24 Mar 2000), Wayback capture 2014-10-25 | <https://web.archive.org/web/20141025044650id_/http://www.tsj.gob.ve/legislacion/constitucion1999.htm> | 2026-10-28 | 1 | Official text (as above). |
| Asamblea Nacional, constitucion-nacional PDF (1999 text, G.O. 36.860 heading) | <https://www.asambleanacional.gob.ve/storage/documentos/botones/constitucion-nacional-20191205135853.PDF> | 2026-10-28 | 1 | Official text (as above). |
| Tribunal Supremo de Justicia, /constitucion and /codigos index pages | <https://www.tsj.gob.ve/constitucion> | 2026-10-28 | 27 | Official site. |

Every response is cached by the sha256 of its URL, and the table above lists every source with its retrieval date. Lexifina keeps its fetch scripts privately; `tools/parse.py` reads only the cache and writes `corpus.json`, so the same cache always gives the same corpus.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `constitucion` | Constitución de la República Bolivariana de Venezuela | 2 | 1999-12-30 to 2009-02-19 |

The build made 2 commits:

| Commits | Kind |
| ---: | --- |
| 1 | first version of an act |
| 1 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `futuro`: laws not yet in force on 2026-10-28.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 2 laws in the record.
- 4 tags.

## Dates

Each commit is dated at noon (America/Caracas) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: Código Civil art. 1: "La Ley es obligatoria desde su publicación en la GACETA OFICIAL o desde la fecha posterior que ella misma indique." A law's own vigencia clause overrides this. https://historico.tsj.gob.ve/legislacion/ (Código Civil, G.O. 2.990 Ext., 26 Jul 1982)

## Commands, in order

```sh
# fill the cache from the sources listed above (network; Lexifina's fetch scripts are kept privately)
python -X utf8 tools/parse.py                  # cache -> corpus.json (no network)
python -X utf8 tools/build.py <folder> --repo <empty folder> --docs-date 2026-10-28
python -X utf8 tools/check_repo.py <repo> --corpus <folder>/corpus.json --write
python -X utf8 tools/build.py <folder> --repo <another empty folder> --docs-date 2026-10-28 --compare <repo>
```

In the main Lexifina repository these files live as follows:
- `fetch.py`, `parse.py` and `repo/`: in `scripts/venezuela-law/`.
- `build.py`, `check_repo.py` (`check.py` there) and `on.py`: in `scripts/gitlaw_common/`, with the corpus format in `SCHEMA.md`.

## Exact inputs

- `corpus.json` sha256 `047a462c48f4a95ea7ab836563cacfcae00cd7d1c15b5bf11aa7b3aba16b1540` (582212 bytes)
- Script blob hashes (`git hash-object`):

| Script | Blob |
| --- | --- |
| build.py | `727357e12b2533e202258d8bf11c2b5d869ca8f6` |
| check.py | `0f457d2b473ba31682d0c0b32e9dcad30e613895` |
| on.py | `644a6c0857fbcc72562032b58d57aa113fee0641` |
| fetch.py | `370cd81cc5072e32eb9d64bec59ef793a6643f60` |
| parse.py | `c91d775124b8b661d3fedee878094ed64984eb80` |

- Tools:
  - Python 3.14.0
  - git version 2.52.0.windows.1
  - curl 8.21.0 (Windows) libcurl/8.21.0 Schannel zlib/1.3.2 WinIDN WinLDAP

## Checks

Not yet run for this build.

Not yet run for this build.

These results are from the check run on the build before this one, from the same corpus.

## Decisions made by hand

- Constitution text: G.O. 5.908 Ext. of 19 Feb 2009 (the latest full official printing, ordered by Enmienda N° 1 art. 2), read from the text layer of the copy hosted by the Instituto Nacional de Estadística (ine.gob.ve). The TSJ and Asamblea Nacional copies of 5.908 and 5.453 are image scans and this machine has no OCR, so they were not used for text.
- Version 1 (from 1999-12-30) is the 5.908 body text with the original wording of arts. 160, 162, 174, 192 and 230 (which the reprint keeps, each followed by a '(Ver Enmienda N° 1 ...)' note, per Const. art. 341.5). It is cross-checked word by word against two independent official transcriptions of the 1999 text: the TSJ HTML of G.O. 5.453 and the Asamblea Nacional PDF; every difference is listed in PROGRESS.md.
- The original publication (G.O. 36.860, 30 Dec 1999) was reprinted 'por error material del ente emisor' in G.O. 5.453 Ext. (24 Mar 2000). No text-layer copy of 36.860 was found, so the corrections are not a separate version: version 1 carries the corrected wording from 1999-12-30 (its in-force day, Disposición final única).
- Version 2 (from 2009-02-19, the day of publication; the Enmienda names no other date, Código Civil art. 1) replaces the operative text of the five articles with the Enmienda's wording; the '(Ver Enmienda ...)' notes are dropped from the text.
- The Constitution of 1999 is credited as a referendum (approved 15 Dec 1999, proclaimed 20 Dec 1999); the Enmienda N° 1 as a referendum (approved 15 Feb 2009).
- One file per article, transitional provision, derogatory and final provision; the Preamble in preambulo.md; the closing approval paragraph in promulgacion.md; the headings of titles, chapters and sections, in order, in titulos.md. The lists of signatories are omitted. The Exposición de Motivos (in G.O. 5.453, not in 5.908) is not normative and is not included.
- The INE copy of G.O. 5.908 lacks some lines of text (mostly the last line of a page; the words are not in the PDF). parse.py aligns it word by word with the Asamblea Nacional text and restores 12 gaps from it, in units art-033, art-049, art-089, art-156, art-178, art-187, art-270, art-293, art-332, disp-transitoria-03, disp-transitoria-04. Every restored passage is listed in PROGRESS.md. The remaining differences between the two are spellings of compound words ('politicoterritorial' in 5.908, 'político territorial' in the AN text) and two AN typos; the 5.908 spelling is kept.
- Paragraphs are rebuilt from the PDF layout: wrapped lines are joined, page numbers dropped, a blank line ends a paragraph only after . : ; or ), and numbered/lettered items start their own line. Spellings are kept as printed in G.O. 5.908.
- PDF text extraction: pdftotext version 4.00 with -enc UTF-8 -layout.

## What AI did and did not do

The fetch, parse and check scripts were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above, through code that anyone can rerun.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: no model wrote, summarised or corrected any legal text; parsing is rule-based (parse.py).
