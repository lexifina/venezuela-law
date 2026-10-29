# Venezuela: law history in git

The law of Venezuela as a git history: one file per provision, one commit per act on the day it took effect, and the act that made each change as the commit's author. `git blame` names the act behind every paragraph; `git log` lists every change to an article; checking out a date gives the text in force that day.

It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law), which places it at `ve/`.

**What is in it now**

| Folder | Act | Versions | History |
| --- | --- | ---: | --- |
| `constitucion/` | Constitución de la República Bolivariana de Venezuela (1999) | 2 | From its entry into force (30 December 1999) to today, through Enmienda N° 1 (19 February 2009) |
| `constitucion-1961/` | Constitución de la República de Venezuela (1961) | 4 | From 23 January 1961, through Enmienda N° 1 (1973) and N° 2 (1983), to its repeal by the Constitution of 1999 (30 December 1999). Arts. 191 and 192 are missing from the source. |
| `codigo-organico-procesal-penal/` | Código Orgánico Procesal Penal (COPP) | 1 | The texto único of the 2021 reform (G.O. 6.644 Ext., 17 September 2021), in force from that day. Earlier texts (1998 to 2012) are scans. |
| `codigo-organico-tributario/` | Código Orgánico Tributario (COT) | 1 | As dictated by Decreto Constituyente (G.O. 6.507 Ext., 29 January 2020), in force from 28 February 2020. The 2014 Code it repeals is a scan. |
| `codigo-organico-penitenciario/` | Código Orgánico Penitenciario (COP) | 1 | The texto único of the 2021 reform (G.O. 6.647 Ext., 17 September 2021). The 2015 text is not on the gazette portal. |
| `codigo-organico-de-justicia-militar/` | Código Orgánico de Justicia Militar (COJM) | 1 | The texto único of the 2021 partial reform (G.O. 6.646 Ext., 17 September 2021). |
| `ley-organica-del-tribunal-supremo-de-justicia/` | Ley Orgánica del Tribunal Supremo de Justicia (LOTSJ) | 1 | The texto único of the 2022 reform (G.O. 6.684 Ext., 19 January 2022). The 2010 Law is a scan. |
| `ley-del-impuesto-al-valor-agregado/` | Ley que Establece el Impuesto al Valor Agregado (IVA) | 1 | The texto único of the 2020 reform (G.O. 6.507 Ext., 29 January 2020), in force from 29 March 2020. The 2018 reform is a scan. |
| `ley-organica-de-aduanas/` | Ley Orgánica de Aduanas | 1 | The texto único of the 2020 reform (G.O. 6.507 Ext.), in force from 19 February 2020. The 2014 text is a scan. |
| `ley-organica-sobre-el-derecho-de-las-mujeres-a-una-vida-libre-de-violencia/` | Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia | 1 | The texto único of the 2021 reform (G.O. 6.667 Ext., 16 December 2021), in force from that day. |
| `ley-de-impuesto-a-las-grandes-transacciones-financieras/` | Ley de Impuesto a las Grandes Transacciones Financieras (IGTF) | 1 | The texto único of the 2022 reform (G.O. 6.687 Ext., 25 February 2022), in force from 27 March 2022 (art. 25). |
| `ley-contra-la-corrupcion/` | Ley contra la Corrupción | 1 | The texto único of the 2022 reform (G.O. 6.699 Ext., 2 May 2022), in force from that day. The 2003 and 2014 texts are scans. |
| `ley-organica-de-la-defensa-publica/` | Ley Orgánica de la Defensa Pública | 1 | The texto único of the 2022 reform (G.O. 6.702 Ext., 25 May 2022), in force from that day. |
| `ley-organica-de-las-zonas-economicas-especiales/` | Ley Orgánica de las Zonas Económicas Especiales | 1 | As enacted (G.O. 6.710 Ext., 20 July 2022), in force from that day. |
| `ley-organica-de-extincion-de-dominio/` | Ley Orgánica de Extinción de Dominio | 1 | As enacted (G.O. 6.745 Ext., 28 April 2023), in force from that day. |
| `ley-organica-de-hidrocarburos/` | Ley Orgánica de Hidrocarburos | 2 | The texto único of the 2026 reform (G.O. 6.978 Ext., 29 January 2026), in force from that day except arts. 51 and 55-59, which take effect on 31 March 2026. The 2001 and 2006 texts are scans. |
| `ley-organica-para-la-celeridad-y-optimizacion-de-tramites-administrativos/` | Ley Orgánica para la Celeridad y Optimización de Trámites Administrativos | 1 | As enacted (G.O. 7.018 Ext., 8 April 2026), in force from that day. |
| `ley-organica-de-minas/` | Ley Orgánica de Minas | 1 | As enacted (G.O. 7.020 Ext., 16 April 2026), in force from that day. It repeals the Ley de Minas of 1999 and the 2015 law reserving gold and strategic minerals to the State, which are not in this record. |

The sixteen acts after the Constitutions each start at their latest full official printing, the first that exists as text. Their histories begin there; each first commit is credited to the publisher as "oldest version available", not to the reform law, because it is not the act as first enacted. The exceptions are the COT, the Ley Orgánica de las Zonas Económicas Especiales, the Ley Orgánica de Extinción de Dominio, the Ley Orgánica para la Celeridad y Optimización de Trámites Administrativos and the Ley Orgánica de Minas, which are printed as enacted and credited to the act itself. The Ley Orgánica de Hidrocarburos has a second version, for the six articles whose new wording took effect sixty days after the rest.

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

## Codes and laws read from the gazette (2020-2026)

- **Source.** Each is the act's full reprint ("texto único") in the Gaceta Oficial, downloaded from gacetaoficial.gob.ve. From about 2018 on, the gazettes there are born-digital PDFs with a text layer; earlier ones are image scans.
- **Only printed text.** These gazettes are made of text frames pasted on white boxes. Their text layer also holds words that are never printed: frame overflow cut off by the frame's edge (repeated at the top of the next page) and older text painted over by a later white box. A plain text extraction (pdftotext) prints all of it, for example item 8 of COPP art. 111 twice. `tools/gazette_text.py` keeps only the characters the page actually paints, decided from the PDF's own drawing instructions: the clip of each frame and the order in which text and white boxes are drawn. No page image is rendered or recognised (no OCR).
- **Checks**. For each act, the words in its files equal the words printed in its part of the gazette. Every word dropped from the text layer is listed; each dropped run is either printed elsewhere in the act (overflow) or a hidden page header or footer. Every article number from 1 to the last occurs once.
- **One restored passage.** COJM art. 187 sits below the bottom edge of its page, so the printed page omits it; it is restored from the text layer and listed in `REPRODUCE.md`. One COJM chapter heading (Capítulo III, before art. 30) is painted over on the page and is left out.
- **Repairs in the acts of 2021-2026.** Each is listed in `REPRODUCE.md`. In the Ley Orgánica sobre el Derecho de las Mujeres, two passages the gazette prints twice in a row are read once, and the last two lines of item 5 of art. 19, which sit below the frame and are printed nowhere, are restored. In the Ley Orgánica de Hidrocarburos, white boxes laid over the source document's page numbers also cover the ends of 13 printed lines and the epigraph of art. 2; those words are read from the text layer. Fragments of the source documents' page footers and of the masthead are dropped. Art. 11 of the Ley Orgánica de Extinción de Dominio ends "..., b" as printed. In the Ley Orgánica de Minas, art. 117 is printed without its final stop; the flush-right line after it is read as the epigraph of art. 118.
- **Hydrocarbons, two dates.** The Ley Orgánica de Hidrocarburos took effect on publication, 29 January 2026, except arts. 51 and 55-59, which took effect once sixty continuous days following publication had run: from 31 March 2026 (Disposición final única). Until then arts. 56-59, inserted by the reform, are absent, and arts. 51 and 55, which the reform reworded, read "[La fuente no da el texto vigente en esta fecha.]", because their 2006 wording survives only as a scan.
- **In force.** COPP, COP and COJM took effect on publication, 17 September 2021; the LOTSJ on publication, 19 January 2022 (Disposición final tercera); the COT thirty continuous days after publication, 28 February 2020 (art. 352); the IVA law sixty continuous days after publication, 29 March 2020 (art. 72); the Ley Orgánica de Aduanas once twenty continuous days had run from the day after publication, 19 February 2020 (art. 195). The Ley contra la Corrupción (2 May 2022), the Ley Orgánica de la Defensa Pública (25 May 2022), the Ley Orgánica sobre el Derecho de las Mujeres (16 December 2021), the Ley Orgánica de las Zonas Económicas Especiales (20 July 2022) the Ley Orgánica de Extinción de Dominio (28 April 2023), the Ley Orgánica para la Celeridad y Optimización de Trámites Administrativos (8 April 2026) and the Ley Orgánica de Minas (16 April 2026) took effect on publication; the IGTF law thirty continuous days after publication, 27 March 2022 (art. 25; the Asamblea Nacional's page gives 28 March). The days that are counted are counted by hand, and the reasoning is in `REPRODUCE.md`.
- **Typesetting.** Spellings are kept as printed (for example "Artículos 304." and "Artículo 577-." in the COJM). The only changes: a space after "Artículo N." where none is printed, and "A rtículo" (a kerned capital read as a separate glyph) joined to "Artículo".
- **Later reforms.** The LOTSJ was reformed twice in 2026, each time with a new texto único (G.O. 7.025 Ext., 22 May 2026, and G.O. 7.074 Ext., 15 September 2026); those two versions are not yet in this record. No later reform of the other acts was found in the extraordinary gazettes of 2026 (to October).

## How it is checked

- Every version of every act is read back from git on the day it took effect and on the day before (`tools/check_repo.py`); both must match `corpus.json`. Results are in `REPRODUCE.md`.
- Health checks: no merge commits on `main`, commit dates never go backwards, nothing dated in the future, and every commit's trailers parse with `git interpret-trailers --parse`.
- The repository is rebuilt from the same data a second time and must give identical hashes.

## What "author" means

The author of a commit is the act that made the change, with an e-mail address that cannot exist (`enmienda-1-2009@gacetaoficial.invalid`), so `git blame` and `git log --author` name acts. The committer is always Lexifina.

- **Credits come only from the source.** The changes of 2009 are credited to Enmienda N° 1 because the gazette prints the Enmienda and notes it under each article it changes.
- Both the Constitution of 1999 and Enmienda N° 1 were approved by referendum, so their commits are of kind "referendum".

## What it does not show

- **The Código Civil (1982), the Código Penal (2005) and the Código de Comercio (1955).** The only official copies found are image scans: the TSJ's gazette PDFs (for example G.O. 5.768 Ext. for the Código Penal), the Asamblea Nacional's copy of the Código de Comercio, and the gazette portal, which has nothing before 2010. This record uses no OCR, and copies held by non-Venezuelan bodies are not official texts, so these codes are not here. The same holds for most laws before about 2018.
- **A data protection law.** No general data protection law was found: none is among the Asamblea Nacional's law pages captured by the Internet Archive (393 pages, to January 2026). The nearest acts, the Ley Especial contra los Delitos Informáticos (2001) and the Ley de Mensajes de Datos y Firmas Electrónicas (2001), exist online only as TSJ transcriptions of the sanctioned text or as scans.
- **Versions of the codes before their latest printing.** COPP 1998-2012, COT 2014, COP 2015, LOTSJ 2010, IVA 2018, Aduanas 2014 and the earlier texts of the laws added from 2021-2026 gazettes exist only as scans or not at all online, so each history starts at its 2020-2026 printing.
- **Labour, securities, banking, income tax and fair-prices laws.** The LOTTT (2012), the Ley Orgánica Procesal del Trabajo (2002), the Ley de Mercado de Valores (2015), the Ley de Instituciones del Sector Bancario (2014), the Ley de Impuesto sobre la Renta (2015) and the Ley Orgánica de Precios Justos (2015) have no full printing after 2018 found on the portal or in the Asamblea Nacional's list, and their gazettes are scans, so they are not here. Gazettes of 2015-2018 on the portal have a text layer only on their first pages.

- **The text as first printed in G.O. 36.860** (see above).
- **The Exposición de Motivos.** It is printed with the Constitution in G.O. 5.453 but is not part of the normative text, and is not in G.O. 5.908.
- **The lists of signatories** of the Asamblea Nacional Constituyente.
- **Rulings of the Sala Constitucional** that interpret the Constitution. They change no words, and none is recorded yet.
- **The rejected constitutional reform of 2007.** It was rejected by referendum on 2 December 2007 and changed nothing.

## How it is built

Lexifina reads the sources listed here and records each act's dated versions, and the laws that made each change, in one corpus file. `tools/build.py` writes this repository from that file, and the same corpus always gives the same commit hashes; `REPRODUCE.md` gives the details and the checks. A model (Claude) wrote Lexifina's code; it wrote no legal text, and no model runs when the history is built.

Lexifina's code writes one part per code or law in `corpus.d/`, reading the gazettes with `tools/gazette_text.py` (PyMuPDF).

No AI model wrote or changed legal text. Claude Opus 5.5 wrote the scripts and chose the sources; see `REPRODUCE.md`.

## Sources

| Source | Kind | Past versions by date | Names the amending act | Bulk | Notes |
| --- | --- | --- | --- | --- | --- |
| [Gaceta Oficial (gacetaoficial.gob.ve)](http://www.gacetaoficial.gob.ve) | Official gazette | gazettes from 2010 only | n/a | JSON day index `gacetas/dia?year=&month=&day=` | HTTP only. Earlier gazettes are not indexed. Used: G.O. 6.507, 6.644, 6.646, 6.647, 6.667, 6.684, 6.687, 6.699, 6.702, 6.710, 6.745 and 6.978 Ext. (born-digital, 2020-2026) for the fourteen codes and laws. |
| [Imprenta Nacional](http://www.imprentanacional.gob.ve) | Official printer | no | n/a | no | Landing page only. Over 100 gazettes are reported never to have been released. |
| [Tribunal Supremo de Justicia](https://www.tsj.gob.ve/constitucion) | Court; gazette PDFs | constitutions since 1811; codes | n/a | no | Reachable only now and then from abroad. Its PDFs of G.O. 5.453 and 5.908 are image scans, and its link to the Enmienda is broken. |
| [Asamblea Nacional](https://www.asambleanacional.gob.ve/leyes/vigentes) | Legislature | no | n/a | lists of laws in force and laws passed | Used: the 1999 text (with a text layer), to fill the gaps in the INE copy. Its copy of G.O. 5.908 is a scan. |
| [Instituto Nacional de Estadística](https://ine.gob.ve) | State body | no | n/a | no | Used: G.O. 5.908 with a text layer. |
| [Internet Archive](https://web.archive.org) | Archive | captures | n/a | – | Older TSJ pages. Captures are pinned by timestamp. |

Research guides that cover every country: [GlobaLex](https://www.nyulawglobal.org/globalex/) and the [Law Library of Congress Guide to Law Online](https://www.loc.gov/research-centers/law-library-of-congress/researcher-resources/guide-to-law-online/).

## Licence

The legal texts are official acts of the Bolivarian Republic of Venezuela, published in the Gaceta Oficial. The arrangement, tables, commit messages and tools are by Lexifina, under the terms in `LICENSE`.

This repository is not legal advice and not an official publication.

## En español

Historia del derecho venezolano en git: un archivo por disposición y un commit por acto, fechado el día de su entrada en vigencia y firmado por el acto que hizo el cambio (`git blame` nombra el acto de cada párrafo). Contiene la Constitución de la República Bolivariana de Venezuela desde su entrada en vigencia el 30 de diciembre de 1999, con la Enmienda N° 1 aprobada por referendo el 15 de febrero de 2009 (G.O. N° 5.908 Extraordinario, 19 de febrero de 2009), y la Constitución de 1961 con sus Enmiendas N° 1 (1973) y N° 2 (1983) hasta su derogación en 1999 (faltan los arts. 191 y 192 en la fuente). También contiene, desde su última publicación íntegra en la Gaceta Oficial, el Código Orgánico Procesal Penal (G.O. 6.644 Ext., 2021), el Código Orgánico Tributario (G.O. 6.507 Ext., 2020), el Código Orgánico Penitenciario (G.O. 6.647 Ext., 2021), el Código Orgánico de Justicia Militar (G.O. 6.646 Ext., 2021), la Ley Orgánica del Tribunal Supremo de Justicia (G.O. 6.684 Ext., 2022), la Ley que Establece el Impuesto al Valor Agregado y la Ley Orgánica de Aduanas (G.O. 6.507 Ext., 2020), la Ley Orgánica sobre el Derecho de las Mujeres a una Vida Libre de Violencia (G.O. 6.667 Ext., 2021), la Ley de Impuesto a las Grandes Transacciones Financieras (G.O. 6.687 Ext., 2022), la Ley contra la Corrupción (G.O. 6.699 Ext., 2022), la Ley Orgánica de la Defensa Pública (G.O. 6.702 Ext., 2022), la Ley Orgánica de las Zonas Económicas Especiales (G.O. 6.710 Ext., 2022), la Ley Orgánica de Extinción de Dominio (G.O. 6.745 Ext., 2023), la Ley Orgánica de Hidrocarburos (G.O. 6.978 Ext., 2026; sus arts. 51 y 55-59 rigen desde el 31 de marzo de 2026), la Ley Orgánica para la Celeridad y Optimización de Trámites Administrativos (G.O. 7.018 Ext., 2026) y la Ley Orgánica de Minas (G.O. 7.020 Ext., 2026); de estas gacetas se toma solo el texto impreso en la página, no el texto oculto de su capa de texto. El Código Civil, el Código Penal y el Código de Comercio no se incluyen, porque sus únicas copias oficiales son imágenes escaneadas.

- Texto vigente en una fecha: `python tools/en_vigor_el.py 2005-01-01 constitucion 230`
- Fechas: regla supletoria del art. 1 del Código Civil (la ley es obligatoria desde su publicación en la Gaceta Oficial, o desde la fecha posterior que ella misma indique).
- Texto: G.O. N° 5.908 Extraordinario. Las pocas líneas que faltan en la copia del INE se completaron con el texto de la Asamblea Nacional, y cada una consta en `REPRODUCE.md`. La primera impresión (G.O. 36.860) no se muestra, porque no se halló una copia legible por máquina.
- Ningún modelo de IA escribió texto legal.
