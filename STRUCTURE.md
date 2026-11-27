# Estructura / Structure

| Carpeta / Folder | Contenido / What it holds |
| --- | --- |
| `constitucion/` | Constitución de la República Bolivariana de Venezuela (1999, con la Enmienda N° 1 de 2009) |
| `constituciones-historicas/1961/` | Constitución de 1961 con sus dos enmiendas, hasta 1999 |
| `codigos/<código>/` | Códigos (Civil, Penal, de Comercio, de Procedimiento Civil, orgánicos) y la LOTTT, p. ej. `codigos/codigo-civil/` |
| `leyes/<año>/<número de gaceta>-<ley>/` | Leyes y decretos con rango, valor y fuerza de ley, por el año y el número de la Gaceta Oficial de su versión más antigua aquí, p. ej. `leyes/2022/6711-ley-de-sellos/` |
| `decretos/<año>/<número de gaceta>-<decreto>/` | Decretos y reglamentos |
| `resoluciones/<año>/<número de gaceta>-<resolución>/` | Resoluciones ministeriales |
| `providencias/<año>/<número de gaceta>-<providencia>/` | Providencias administrativas |
| `otros/<año>/<número de gaceta>-<acto>/` | Otros actos normativos |

Cada carpeta de un acto tiene un archivo por artículo (`art-001.md`; `art-0137.md` en los códigos de más de 999
artículos, que se reparten en subcarpetas `articulos-0001-0500/` ... para no pasar de 1.000 entradas por carpeta),
`titulos.md` con los libros, títulos, capítulos y secciones, y un `README.md` con la lista de disposiciones. Un acto
sin artículos numerados tiene un solo `texto.md`.

Each act folder holds one file per article, `titulos.md` with its headings and a `README.md` listing the files; codes
of more than 999 articles are split into `articulos-0001-0500/` ... sub-folders so that no folder holds more than
1,000 entries.

## Fechas / Dates

Cada versión es un commit fechado a las 12:00 de America/Caracas del día en que entró en vigencia, repetido en el
trailer `In-force:`; `In-force-basis:` dice de dónde viene ese día: la disposición de vigencia del propio acto, o, si
no tiene, su publicación en la Gaceta Oficial (Código Civil, art. 1: "La Ley es obligatoria desde su publicación en la
GACETA OFICIAL o desde la fecha posterior que ella misma indique"). Un acto sin día de publicación fiable, o cuya
vigencia depende de un plazo o condición que no se calcula aquí, no se incluye. Antes de 1970 (que git no puede
guardar) el commit lleva la fecha 1970-01-01 y el día real en el asunto y en `In-force:`. Ninguna fecha es el día de
descarga.

`Source-status: secondary copy (...)` marks a text taken from FAOLEX (FAO) or WIPO Lex because the official gazette
and court hosts (gacetaoficial.gob.ve, tsj.gob.ve) do not answer from here; `Text-source: publisher OCR` marks a text
layer the publisher made by OCR (no OCR is run here).
