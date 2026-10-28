# Venezuela: law history in git

The law of Venezuela as a git history: one file per provision, one commit per act on the day it took effect, and the act that made each change as the commit's author. `git blame` names the act behind every paragraph; `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `ve/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitucion/` | Constitución de la República Bolivariana de Venezuela (1999) | 2 | From its entry into force (30 December 1999) to today, through Enmienda N° 1 (19 February 2009) |
| `constitucion-1961/` | Constitución de la República de Venezuela (1961) | 4 | From 23 January 1961, through Enmienda N° 1 (1973) and N° 2 (1983), to its repeal by the Constitution of 1999 (30 December 1999). Arts. 191 and 192 are missing from the source. |

Venezuela has no official consolidated database with dated versions. The only sources are the Gaceta Oficial, published as PDFs (most of them image scans) and only indexed online from 2010, plus copies on the sites of the Tribunal Supremo de Justicia (TSJ), the Asamblea Nacional and other bodies. Over 100 gazettes are reported never to have been released. So each history here is rebuilt from the gazettes that reprint an act in full, and it is only as long as those sources allow.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What did art. 230 of the Constitution say on 1 January 2005? | `python tools/en_vigor_el.py 2005-01-01 constitucion 230` |
| The same, with raw git (bash) | `git show $(git rev-list -1 --before="2005-01-01T23:59:59Z" main -- constitucion/art-230.md):constitucion/art-230.md` |
| The same, in PowerShell | `$r = git rev-list -1 --before="2005-01-01T23:59:59Z" main -- constitucion/art-230.md; git show "$($r):constitucion/art-230.md"` |
| Which act wrote each paragraph of art. 160? | `git blame constitucion/art-160.md` |
| Every change to art. 230, word by word | `git log -p --word-diff constitucion/art-230.md` |
| Every act in the record, in order | `git log --reverse --format="%ad %an" --date=short main` |
| Everything one act changed | `git show law/enmienda-1-2009` (tags `law/<key>` mark each act's commit) |
| The whole Constitution on a date | `python tools/en_vigor_el.py 2005-01-01 constitucion` |
| Acts passed but not yet in force | `git log main..futuro` |

After a rebuild, refresh tags with `git fetch --force --tags`: a plain fetch keeps stale tags.

## Dates

- Each commit is dated at **noon, America/Caracas, on the day the change took effect** (the in-force date). Enactment and publication dates are trailers (`Enacted:`, `Published:`), and the in-force day is in `In-force:`, which the tools read.
- **Default rule.** Código Civil art. 1: "La Ley es obligatoria desde su publicación en la GACETA OFICIAL o desde la fecha posterior que ella misma indique." An act's own vigencia clause overrides it.
- **The Constitution of 1999** was approved by referendum on 15 December 1999, proclaimed by the Asamblea Nacional Constituyente on 20 December 1999 and, by its Disposición final única, took effect on its publication in the Gaceta Oficial N° 36.860 of 30 December 1999. Its first commit is dated 1999-12-30.
- **Enmienda N° 1** was approved by referendum on 15 February 2009 and published, with the whole Constitution reprinted, in the Gaceta Oficial N° 5.908 Extraordinario of 19 February 2009. It names no other date, so it took effect that day.
- **The Constitution of 1961** was sanctioned by Congress on 23 January 1961 and ordered executed that day. Its enmiendas were promulgated on 11 May 1973 (N° 1) and 26 March 1983 (N° 2). Those promulgation days, printed in the text, are taken as the days of publication and entry into force; the gazettes themselves are scans and were not read.
- Git cannot store dates before 1970. The 1961 commit is dated 1 January 1970, and its real day, 1961-01-23, is in the `In-force:` trailer, which the tools read.

## Where the text comes from

- **The Constitution's text is G.O. N° 5.908 Extraordinario (2009),** the latest full official printing, read from the text layer of the copy hosted by the Instituto Nacional de Estadística. Following art. 341.5 of the Constitution, that printing keeps the 1999 wording of the five amended articles (160, 162, 174, 192 and 230), notes "(Ver Enmienda N° 1 ...)" under each, and prints the Enmienda after the Constitution.
  - The 1999 version is the reprint's body text, with the original wording of those five articles.
  - The 2009 version gives them the Enmienda's wording. The "(Ver Enmienda ...)" notes are not in the text.
- **The INE copy lacks a few lines.** Some lines are missing from the PDF itself, mostly the last line of a page: 11 gaps, in arts. 33, 49, 89, 156, 178, 187, 270, 293 and 332 and in the Cuarta transitoria (twice), and one lost initial ("ara" for "Para" in the Tercera transitoria).
  - Each gap was filled from the Asamblea Nacional's text of 1999 after a word-by-word comparison. Each filled passage is listed in `REPRODUCE.md`.
  - After that, the two texts differ only in how compound words are spelt ("politicoterritorial" in 5.908, "político territorial" in the AN text) and in a few AN typos ("postrado", "contenciosa electoral", "auditoria"). The 5.908 spelling is kept.
- **The first printing is not shown.** The original publication of December 1999 (G.O. 36.860) was reprinted "por error material" in G.O. 5.453 Extraordinario of 24 March 2000. No machine-readable copy of 36.860 was found, so the 1999 version already has the corrected wording.
  - The TSJ's HTML transcription labelled 5.453 differs in wording from both 5.908 and the AN text in more than 80 articles. It was not used.

## The Constitution of 1961

- **Source.** The text comes from the TSJ's text-layer PDF of the 1961 Constitution as reprinted after Enmienda N° 2, read from a Wayback capture (2011) of `tsj.gov.ve/legislacion/constitucion1961.pdf`. No second machine-readable source was found to cross-check it.
- **Enmiendas.** Under art. 245.6 of that Constitution, an enmienda is a separate text published after the Constitution, with a note under each article it concerns. The articles' words do not change. So each enmienda's operative articles are files of their own (`enmienda-01-art-001.md`, `enmienda-02-art-001.md` to `-008.md`), added on the day the enmienda took effect. The commit message names the articles each one concerns.
- **Arts. 191 and 192 are missing** from the TSJ transcription: art. 190 runs straight into art. 193. They are therefore absent from every version.
- **The Disposiciones Transitorias** are a separate text sanctioned with the Constitution (art. 251). They are in `disp-transitoria-01.md` to `-23.md`, without the reprint's "Cumplida" notes.
- **Repeal.** On 30 December 1999 the Disposición derogatoria única of the new Constitution repealed it, and every file is removed in a commit credited to the Constitution of 1999.

## How it is checked

- Every version of every act is read back from git on the day it took effect and on the day before (`tools/check_repo.py`); both must match `corpus.json`. Results are in `REPRODUCE.md`.
- Health checks: no merge commits on `main`, commit dates never go backwards, nothing dated in the future, and every commit's trailers parse with `git interpret-trailers --parse`.
- The repository is rebuilt from the same data a second time and must give identical hashes.

## What "author" means

The author of a commit is the act that made the change, with an e-mail address that cannot exist (`enmienda-1-2009@gacetaoficial.invalid`), so `git blame` and `git log --author` name acts. The committer is always Lexifina.

- **Credits come only from the source.** The changes of 2009 are credited to Enmienda N° 1 because the gazette prints the Enmienda and notes it under each article it changes.
- Both the Constitution of 1999 and Enmienda N° 1 were approved by referendum, so their commits are of kind "referendum".

## What it does not show

- **The Código Civil (1982) and the Código Penal (2005).** The only official copies found are image scans: the TSJ's gazette PDFs (for example G.O. 5.768 Ext. for the Código Penal) and the gazette portal, which has nothing before 2010. This machine has no OCR, and copies held by non-Venezuelan bodies are not official texts, so neither code is here yet. The same holds for most laws before about 2018: from then on, the gazettes on gacetaoficial.gob.ve have a text layer.
- **The Código Orgánico Procesal Penal (2021).** Its texto único in G.O. 6.644 Ext. has a text layer, but the layer also holds hidden overlaid text: some items appear twice, once with stray words. That cannot be told apart from the printed text without looking at the page, so the code is not here yet. Its earlier versions (1998 to 2012) are scans.

- **The text as first printed in G.O. 36.860** (see above).
- **The Exposición de Motivos.** It is printed with the Constitution in G.O. 5.453 but is not part of the normative text, and is not in G.O. 5.908.
- **The lists of signatories** of the Asamblea Nacional Constituyente.
- **Rulings of the Sala Constitucional** that interpret the Constitution. They change no words, and none is recorded yet.
- **The rejected constitutional reform of 2007.** It was rejected by referendum on 2 December 2007 and changed nothing.

## How it is built

`tools/fetch.py` downloads every source once through curl, cached by the sha256 of the URL, at most one request per second per host. `tools/parse.py` turns the cache into `corpus.json`, using `pdftotext` (xpdf 4.00) for PDFs. The shared builder `tools/build.py` writes the history with `git fast-import`, and the same corpus always gives the same hashes. `REPRODUCE.md` records every command, tool version, data hash and decision, and the result of a hash-for-hash rebuild.

No AI model wrote or changed legal text. Claude Opus 5.5 wrote the scripts and chose the sources; see `REPRODUCE.md`.

## Sources

| Source | Kind | Past versions by date | Names the amending act | Bulk | Notes |
| --- | --- | --- | --- | --- | --- |
| [Gaceta Oficial (gacetaoficial.gob.ve)](http://www.gacetaoficial.gob.ve) | Official gazette | gazettes from 2010 only | n/a | JSON day index `gacetas/dia?year=&month=&day=` | HTTP only. Earlier gazettes are not indexed. |
| [Imprenta Nacional](http://www.imprentanacional.gob.ve) | Official printer | no | n/a | no | Landing page only. Over 100 gazettes are reported never to have been released. |
| [Tribunal Supremo de Justicia](https://www.tsj.gob.ve/constitucion) | Court; gazette PDFs | constitutions since 1811; codes | n/a | no | Reachable only now and then from abroad. Its PDFs of G.O. 5.453 and 5.908 are image scans, and its link to the Enmienda is broken. |
| [Asamblea Nacional](https://www.asambleanacional.gob.ve/leyes/vigentes) | Legislature | no | n/a | lists of laws in force and laws passed | Used: the 1999 text (with a text layer), to fill the gaps in the INE copy. Its copy of G.O. 5.908 is a scan. |
| [Instituto Nacional de Estadística](https://ine.gob.ve) | State body | no | n/a | no | Used: G.O. 5.908 with a text layer. |
| [Internet Archive](https://web.archive.org) | Archive | captures | n/a | CDX | Older TSJ pages. Captures are pinned by timestamp. |

Research guides that cover every country: [GlobaLex](https://www.nyulawglobal.org/globalex/) and the [Law Library of Congress Guide to Law Online](https://www.loc.gov/research-centers/law-library-of-congress/researcher-resources/guide-to-law-online/).

## Licence

The legal texts are official acts of the Bolivarian Republic of Venezuela, published in the Gaceta Oficial. The arrangement, tables, commit messages and tools are by Lexifina, under the terms in `LICENSE`.

This repository is not legal advice and not an official publication.

## En español

Historia del derecho venezolano en git: un archivo por disposición y un commit por acto, fechado el día de su entrada en vigencia y firmado por el acto que hizo el cambio (`git blame` nombra el acto de cada párrafo). Contiene la Constitución de la República Bolivariana de Venezuela desde su entrada en vigencia el 30 de diciembre de 1999, con la Enmienda N° 1 aprobada por referendo el 15 de febrero de 2009 (G.O. N° 5.908 Extraordinario, 19 de febrero de 2009), y la Constitución de 1961 con sus Enmiendas N° 1 (1973) y N° 2 (1983) hasta su derogación en 1999 (faltan los arts. 191 y 192 en la fuente). El Código Civil y el Código Penal no se incluyen todavía, porque sus únicas copias oficiales son imágenes escaneadas.

- Texto vigente en una fecha: `python tools/en_vigor_el.py 2005-01-01 constitucion 230`
- Fechas: regla supletoria del art. 1 del Código Civil (la ley es obligatoria desde su publicación en la Gaceta Oficial, o desde la fecha posterior que ella misma indique).
- Texto: G.O. N° 5.908 Extraordinario. Las pocas líneas que faltan en la copia del INE se completaron con el texto de la Asamblea Nacional, y cada una consta en `REPRODUCE.md`. La primera impresión (G.O. 36.860) no se muestra, porque no se halló una copia legible por máquina.
- Ningún modelo de IA escribió texto legal.
