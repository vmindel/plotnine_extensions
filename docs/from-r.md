# Coming from R

| R | plotnine-extensions |
|---|---|
| `ggrepel::geom_text_repel()` | `geom_text_repel()` |
| `ggrepel::geom_label_repel()` | `geom_label_repel()` |
| `ggrastr::rasterise(layer, dpi = 300)` | `rasterise(layer, dpi=300)` |
| `ggrastr::rasterise(plot, layers = "Point")` | `rasterise(p, layers=["point"])` |
| `ggrastr::geom_point_rast()` | `rasterise(geom_point())` |

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
