# Curves and hexagons

## geom_curve

```python
pnx.geom_curve(mapping, data, curvature=0.5, angle=90, arrow=None,
               lineend="butt", shrink=0)
```

- Aesthetics as `geom_segment`: `x`, `y`, `xend`, `yend`, plus colour,
  size, linetype, alpha.
- `curvature`: bow as a fraction of length; positive bows to the right of
  the direction of travel, negative to the left, 0 straight. The sign
  convention is not verified against ggplot2; check the figure.
- `angle` in (0, 180): below 90 skews the bend towards the start, above
  towards the end. Outside that range raises `ValueError`.
- `arrow=arrow(length=0.1, type="closed", ends="last")` (plotnine's
  `arrow`).
- `shrink=12` (points, or `(start, end)`) stops the curve short of its
  ends so arrow heads are not hidden under point markers.
- Computed on screen: the shape does not change with axis scales; a
  quadratic Bezier, so similar to but not identical with ggplot2's spline.

## geom_hex / stat_bin_hex

```python
pnx.geom_hex(bins=30)                 # or binwidth=(bx, by)
pnx.geom_hex(stat="identity", width=0.5, height=0.5)  # precomputed centres
```

- Fill is `after_stat("count")` by default; map
  `aes(fill=after_stat("density"))` for fractions, and `weight` to sum
  weights.
- `bins`: hexagons across each axis (int or `(nx, ny)`). `binwidth=(bx,
  by)`: horizontal centre spacing and vertical spacing within a column.
- All facet panels share one grid.
- Hexagons are regular only when the axes' aspect matches the bin sizes;
  add `coord_fixed()` if regular shapes matter.
- `stat="identity"` needs bin size via `aes(width=, height=)` or
  parameters, else `ValueError`.
- `pnx.hex_bins(x, y, binwidth, origin=(0, 0), weight=None)` returns the
  centres and counts as a DataFrame without plotting.
