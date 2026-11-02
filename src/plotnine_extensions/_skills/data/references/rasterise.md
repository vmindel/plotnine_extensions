# Rasterising layers

```python
pnx.rasterise(obj, dpi=300, layers=None)   # alias: pnx.rasterize
```

- `obj`: a geom, a stat, a layer, a list of these, or a whole `ggplot`.
  Geoms, stats and lists are changed in place and returned; a `ggplot` is
  copied. `layers=["point", "tile"]` (only with a ggplot) picks layers by
  geom name.
- In PDF/SVG/PS output the layer becomes one embedded bitmap per panel
  at `dpi`; axes, text, legends and other layers stay vector.
- PNG/JPEG output: no effect (already a bitmap).
- `dpi` is independent of the `dpi` passed to `save`. `dpi=None` defers
  to matplotlib, i.e. the layer stays vector unless something else
  rasterises it.
- Use for scatter plots with tens of thousands of points, dense tiles,
  per-cell layers: 100,000 points went from about 16 MB to 0.2 MB of PDF
  at 300 dpi.

```python
p = (ggplot(df, aes("umap1", "umap2", color="cluster"))
     + pnx.rasterise(geom_point(size=0.3), dpi=300)
     + pnx.geom_text_repel(aes(label="lab")))   # labels stay vector
p.save("umap.pdf", width=5, height=5)
```

Compared with plotnine's `raster=True`: that rasterises at the save dpi
and only for geoms that forward the flag; `rasterise` works on any geom
and fixes the dpi per layer.
