# Scatterplot matrices (GGally::ggpairs)

```python
pnx.ggpairs(df, columns=["a", "b", "c"], color="group",
            lower="points", diag="density", upper="cor",
            method="pearson", stars=True, adjust=None, digits=2,
            cor_size=9, bins=30, alpha=0.4, labels={"a": "A (log2)"},
            title=None)
```

- Returns **one plain `ggplot`** with
  `facet_grid("yvar ~ xvar", scales="free")`; add themes, scales, layers
  with `+`. Not a GGally ggmatrix: no `p[i, j]` indexing.
- `columns` must be numeric (default: every numeric, non-bool column
  except `color`). A categorical column raises; pass it as `color`.
  Mixed-type panels (box plots, bar charts) are not supported.
- `color` is a **grouping** column, always made categorical. It colours
  points/lines/text and fills densities/histograms. Recolour with
  `scale_color_manual(values=..., aesthetics=["color", "fill"])`, or the
  ribbons keep default colours.
- `lower` / `upper`: `"points"`, `"smooth"` (points + `method="lm"`
  with band), `"density2d"`, `"cor"`, `"blank"`, or a geom / stat /
  layer / list of them, e.g.
  `lower=[geom_point(alpha=0.1, size=0.4), geom_smooth(method="lowess")]`.
  Given layers are copied, restricted to their triangle, and inherit
  `x`, `y`, `color`. `diag` only takes `"density"`, `"hist"`, `"blank"`.
- Diagonal densities/histograms are **rescaled into the row's y range**
  (y axes read in variable units). Density uses R's `bw.nrd0`; per
  group, each integrates to one. Histograms stack groups on shared bins.
- Coefficients: overall line `"Corr: r"` plus one coloured line per
  group. Pairwise-complete rows; `scipy.stats` pearsonr / spearmanr /
  kendalltau. Stars are GGally's (`***` 0.001, `**` 0.01, `*` 0.05,
  `.` 0.1), **unadjusted by default**; `adjust="holm"`/`"bh"` corrects
  across every coefficient drawn.
- Plot data (long): `x`, `y`, `xvar`, `yvar` (the display labels),
  `part` (`"lower"`/`"upper"`) plus every unpaired input column. A
  carried column named `x`, `y`, `xvar`, `yvar` or `part` raises. Only
  raw-data parts have rows: `"cor"`/`"blank"` triangles add none.
- A layer added later draws in both triangles; restrict it with
  `data=lambda d: d[d.part == "lower"]`.
- Many points: `pnx.rasterise(p, layers=["point"])` (big PDF savings).
  Long data is n(n − 1) × rows, so subsample above ~10^5 rows.
- `labels` must stay unique; `cor_size` is points.
