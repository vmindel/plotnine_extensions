# Several scales per aesthetic (ggnewscale)

```python
(
    ggplot(mapping=aes("x", "y"))
    + geom_tile(mat, aes(fill="signal"))      # old fill scale
    + scale_fill_cmap("magma")                # styles the tiles
    + pnx.new_scale_fill()
    + geom_point(pts, aes(fill="cluster"), shape="o")   # new fill scale
    + scale_fill_manual(["#1b9e77", "#d95f02"])         # styles the points
)
```

- `pnx.new_scale_fill()`, `pnx.new_scale_color()` (alias
  `pnx.new_scale_colour`), and `pnx.new_scale("size")` for any
  non-position aesthetic: alpha, color, fill, linetype, shape, size,
  stroke. `pnx.new_scale("color", "fill")` splits two at once. `x`/`y`
  raise `ValueError`.
- **Order decides everything.** Layers, scales, `labs(...)` and
  `guides(...)` for the aesthetic that are in the plot when `new_scale`
  is added belong to the old scale; those added after it to the new
  one. A scale meant for the new layers but placed before `new_scale`
  silently styles the old layers. Put each scale right after its layers.
- Each scale gets its own legend; legends with the same title, labels and
  type merge as usual. Give the scales distinct `name=`.
- Do not map the split aesthetic in `ggplot(aes(...))`: every inheriting
  layer picks it up, earlier ones on the old scale, later ones on the
  new. Map it per layer.
- Constants (`geom_point(color="red")`) are unaffected and not in any
  legend.
- Stat default mappings follow the layer: `geom_bin_2d()`'s default
  `fill=after_stat("count")` before `new_scale_fill()` is on the old
  scale.
- `guides(fill=...)` after `new_scale_fill()` only reaches the new scale;
  for the old one pass `guide=` to its scale or call `guides` before.
- Internally earlier layers' aesthetic is renamed (`fill` to `fill_new1`,
  `fill_new2`, ...) and named back after scale mapping. `after_scale()`
  expressions in earlier layers see the renamed column; stats and
  positions (e.g. `position_jitterdodge`) see the usual names.
