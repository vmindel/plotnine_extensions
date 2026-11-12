# Coming from R

| R | plotnine-extensions |
|---|---|
| `ggrepel::geom_text_repel()` | `geom_text_repel()` |
| `ggrepel::geom_label_repel()` | `geom_label_repel()` |
| `ggrastr::rasterise(layer, dpi = 300)` | `rasterise(layer, dpi=300)` |
| `ggrastr::rasterise(plot, layers = "Point")` | `rasterise(p, layers=["point"])` |
| `ggrastr::geom_point_rast()` | `rasterise(geom_point())` |
| `ggpubr::stat_compare_means(comparisons = ...)` | `stat_compare_means(comparisons=...)` (Holm-corrected by default) |
| `ggsignif::geom_signif()` | `stat_compare_means()`, or `geom_bracket()` for your own p-values |
| `ggpubr::stat_pvalue_manual()` | `geom_bracket()` |
| `ggdist::stat_halfeye()` | `stat_halfeye()` |
| `ggdist::stat_pointinterval()` | `stat_pointinterval()` |
| raincloud (ggdist + jitter) | `geom_raincloud()` |
| `ggseqlogo::geom_logo()` | `logo_data()` + `geom_logo()` |
| `ggplot2::geom_curve()` | `geom_curve()` |
| `ggplot2::geom_hex()` | `geom_hex()` |
| `ggpubr::theme_pubr()`, `theme_pubclean()`, `theme_classic2()` | same names |
| `ggpubr::rremove("x.text")` | `rremove("x.text")`, several names per call |
| `ggpubr::rotate_x_text()`, `grids()`, `border()`, `bgcolor()`, `font()`, `clean_theme()` | same names |
| `cowplot::theme_cowplot()`, `theme_half_open()`, `theme_minimal_grid()`, `theme_minimal_hgrid()`, `theme_minimal_vgrid()`, `theme_map()`, `theme_nothing()` | same names; `line_size` in points (R's 0.5 is 1 here) |
| `cowplot::background_grid()`, `panel_border()` | same names; `size.major` becomes `size_major`, in points |
| `ggcorrplot::ggcorrplot(corr, hc.order = TRUE, p.mat = p)` | `ggcorrplot(corr, hc_order=True, p_mat=p)`; `lab_size` in points |
| `ggcorrplot::cor_pmat(df)` | `cor_pmat(df)`, optionally `adjust="holm"` |
| `ggnewscale::new_scale_fill()`, `new_scale_colour()`, `new_scale("size")` | same names; also `new_scale_color()` |

## ggrepel arguments

Argument names swap dots for underscores. Differences that change
results:

| ggrepel | here | Difference |
|---|---|---|
| `box.padding = 0.25` (lines) | `box_padding=3` (points) | Unit |
| `point.padding = 1e-6` (lines) | `point_padding=0` (points) | Unit |
| `min.segment.length = 0.5` (lines) | `min_segment_length=6` (points) | Unit |
| `point.size = 1` (aesthetic) | `point_size=1.5` (parameter) | Not mappable per point |
| `seed = NA` | `seed=1` | Deterministic by default |
| `max.time = 0.5` | `max_time=1` | |
| `segment.curvature` | not available | Straight segments only |
| `arrow = arrow()` | `arrow={...}` | matplotlib `FancyArrowPatch` options |
| `hjust`, `vjust` | `ha` sets multi-line alignment | Labels are centred on their box |

The placement algorithm is an independent implementation, not a port of
ggrepel, so layouts are comparable but not identical. ggrepel is
GPL-3; this package is MIT.
