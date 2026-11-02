# Repelling labels

```python
pnx.geom_text_repel(mapping=None, data=None, box_padding=3.0,
                    point_padding=0.0, point_size=1.5,
                    min_segment_length=6.0, segment_color=None,
                    segment_size=0.5, segment_alpha=None,
                    segment_linetype="solid", arrow=None, force=1.0,
                    force_pull=1.0, max_iter=10000, max_time=1.0,
                    max_overlaps=10, direction="both", seed=1, xlim=None,
                    ylim=None, nudge_x=0, nudge_y=0)
```

`pnx.geom_label_repel` takes the same plus `geom_label`'s box options
(`boxstyle`, `boxcolor`, `label_padding`, `label_r`, `label_size`) and a
`fill` aesthetic.

- Placement happens when the figure is rendered, on the final panel size
  and output dpi; saving at another size re-places the labels.
- **Label a subset by blanking labels** (`""` or NaN), not by dropping
  rows: unlabelled points still push labels away.
  ```python
  df["lab"] = np.where(df["padj"] < 1e-5, df["gene"], "")
  ```
- `point_size` should equal the `size` of the drawn `geom_point`, so
  labels clear the markers, not only their centres.
- `max_overlaps` drops labels that still overlap more than that many
  labels/points **after** placement; earlier rows win, so sort by priority
  first. A `PlotnineWarning` says how many were dropped. `np.inf` keeps
  all.
- `nudge_x/nudge_y` move the label start; the segment still points at the
  data point (unlike `geom_text`).
- `direction="y"` with `xlim=(x0, None)` lines labels up in a margin
  (e.g. labelling line ends). `xlim`/`ylim` are in data units through the
  scale (work with log and reversed scales).
- `arrow={}` gives arrow heads; the dict goes to matplotlib's
  `FancyArrowPatch` (`{"arrowstyle": "-|>", "mutation_scale": 6}`).
- Units: `box_padding`, `point_padding`, `min_segment_length` and
  `segment_size` are points.
- Dense crowds (> ~60 labels in one region) may hit `max_time` and leave
  overlaps; label fewer points or raise `max_time`.
- Do not pass `adjust_text`; it raises.
