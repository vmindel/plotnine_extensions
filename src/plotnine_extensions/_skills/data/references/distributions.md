# Distributions

Vertical by construction: categories on `x`, values on `y`. For
horizontal plots add `coord_flip()`; do not swap the aesthetics.

## Half-eye

```python
pnx.stat_halfeye(mapping=None, data=None, *, width=0.9, fill="#8fa9c7",
                 adjust=1, scale="area", point="median",
                 widths=(0.66, 0.95), nudge=0, **slab_kwargs)
```

Returns two layers (density slab + point interval). `scale` as in
`geom_violin`: `"area"` (densities on one scale), `"count"`, `"width"`.
Map `fill` in `mapping` to colour slabs by group.

## Raincloud

```python
pnx.geom_raincloud(mapping=None, data=None, *, width=0.6, fill="#8fa9c7",
                   adjust=1, box_width=0.1, jitter=0.06, point_size=0.8,
                   point_alpha=0.5, seed=1)
```

Returns three layers: slab right of the category, narrow box plot on it,
jittered points left of it (two layers with `box_width=0`). After Allen
et al. 2019.

## Building blocks

```python
pnx.stat_pointinterval(point="median", widths=(0.66, 0.95))
pnx.geom_pointinterval(interval_size=(0.6, 1.8), point_size=1.8)
pnx.position_jitternudge(width=0.08, height=0, nudge_x=-0.2, nudge_y=0,
                         random_state=None)
```

- Intervals are equal-tailed quantiles (0.95 spans the 2.5% and 97.5%
  quantiles), not confidence intervals of the median; say so in legends.
- `point` is `"median"` or `"mean"`; `widths` values must be in (0, 1).
- `geom_pointinterval` alone needs `y`, `ymin`, `ymax` and optionally
  `interval_width` mapped.
