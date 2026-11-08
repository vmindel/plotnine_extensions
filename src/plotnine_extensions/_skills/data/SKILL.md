---
name: plotnine-extensions
description: Use when making plotnine (ggplot-style) figures that need what the ggplot2 extension ecosystem provides, via plotnine_extensions (import plotnine_extensions as pnx). Triggers on repelling/non-overlapping text labels (ggrepel), rasterising a dense layer inside a PDF/SVG (ggrastr), significance brackets, p-values or stars between groups (ggpubr, ggsignif), half-eye, interval or raincloud plots (ggdist), sequence logos, contribution-score or ISM logos (ggseqlogo), curved arrows (geom_curve), hexagonal binning (geom_hex), publication themes (theme_pubr, theme_cowplot, rremove, background_grid). Router skill: read the relevant file under references/ before writing code.
---

# plotnine_extensions

ggplot2-extension features for plotnine, as ordinary layers added with
`+`. This file only routes; the reference files hold the signatures,
defaults and the mistakes that give a wrong figure without an error. Read
the file for the task before writing code.

## Task to reference file

| task | read |
|---|---|
| **labels that avoid each other and the points**: `pnx.geom_text_repel`, `pnx.geom_label_repel` | `references/repel.md` |
| **huge PDFs / SVGs from dense layers**: `pnx.rasterise` | `references/rasterise.md` |
| **tests between groups shown as brackets**, or brackets from your own p-values: `pnx.stat_compare_means`, `pnx.geom_bracket` | `references/signif.md` |
| **distributions with summaries**: `pnx.stat_halfeye`, `pnx.geom_raincloud`, `pnx.stat_pointinterval` | `references/distributions.md` |
| **sequence logos**, from sequences or contribution / ISM matrices: `pnx.geom_logo`, `pnx.logo_data` | `references/logo.md` |
| **curved arrows, hexagonal binning**: `pnx.geom_curve`, `pnx.geom_hex` | `references/geoms.md` |
| **ggpubr / cowplot themes** and element helpers: `pnx.theme_pubr`, `pnx.theme_cowplot`, `pnx.theme_minimal_hgrid`, `pnx.rremove`, `pnx.background_grid` | `references/themes.md` |

## Conventions

- `import plotnine_extensions as pnx` alongside `from plotnine import ...`.
- Requires plotnine 0.15.8 or later.
- Functions named `stat_halfeye` and `geom_raincloud` return a **list of
  layers**; add the list with `+` like a single layer. Everything else is
  one layer (or, for `rasterise`, the object you passed in).
- Distances in `geom_text_repel` (`box_padding`, `point_padding`,
  `min_segment_length`) are points, not ggrepel's "lines".
- Defaults chosen for reproducible figures: repel `seed=1`, raincloud
  jitter `seed=1`.
- For genome-browser tracks use the plotnine-genomic-tracks skill instead.
