# Themes (ggpubr, cowplot)

Complete themes replace the current theme; helpers return partial themes,
so add helpers **after** the theme: `+ pnx.theme_pubr() + pnx.rremove("legend")`.
A helper added before a complete theme is wiped out.

## ggpubr

```python
pnx.theme_pubr(base_size=12, base_family=None, border=False, margin=True,
               legend="top", x_text_angle=0)
pnx.theme_pubclean(base_size=12, base_family=None, flip=False)
pnx.theme_classic2(base_size=12, base_family=None)
```

- `theme_pubr`: black axis lines, no grid, legend on top. `border=True`
  boxes the panel instead. `legend` takes `"top"`, `"bottom"`, `"left"`,
  `"right"`, `"none"` or an `(x, y)` inside position.
- `theme_pubclean`: dotted grid on y only; `flip=True` for horizontal
  bars or `coord_flip`.
- Titles are centred (plotnine's default), not left as in ggplot2.

Helpers:

```python
pnx.rremove("x.text", "x.ticks", "legend")   # several names in one call
pnx.rotate_x_text(angle=45)                  # also pnx.rotate_y_text(angle=90)
pnx.grids(axis="y", linetype="dashed", color="#EBEBEB")
pnx.border(color="black")
pnx.bgcolor("#FFF8E7")
pnx.font("title", size=16, color="black", face="bold")
pnx.clean_theme()                            # no axes at all, for marginal plots
```

- `rremove` names: `grid`, `x.grid`, `y.grid`, `axis`, `x.axis`,
  `y.axis`, `xlab`, `ylab`, `xylab`, `legend`, `legend.title`, `ticks`,
  `x.ticks`, `y.ticks`, `axis.text`, `x.text`, `y.text`. Underscores
  also work. Unknown names raise `ValueError`.
- `font` objects: `title`, `subtitle`, `caption`, `xlab`, `ylab`,
  `xylab`, `legend.title`, `legend.text`, `x.text`, `y.text`,
  `xy.text`, `strip.text`. `face` is `"plain"`, `"bold"`, `"italic"` or
  `"bold.italic"`.

## cowplot

```python
pnx.theme_cowplot(font_size=14, font_family=None, line_size=1.0,
                  rel_small=12/14, rel_tiny=11/14, rel_large=16/14)
pnx.theme_half_open()               # same theme as theme_cowplot
pnx.theme_minimal_grid(color="#D9D9D9")
pnx.theme_minimal_hgrid()           # horizontal grid: vertical bars
pnx.theme_minimal_vgrid()           # vertical grid: horizontal bars
pnx.theme_map()                     # no axes; UMAP/t-SNE, images
pnx.theme_nothing()                 # no axes, legend or margin
pnx.background_grid(major="y", minor="none", size_major=1.0, color_major="#D9D9D9")
pnx.panel_border(color="#D9D9D9", size=2.0, remove=False)
```

- `background_grid` removes the directions it does not name, so
  `background_grid(major="y")` on `theme_minimal_grid` leaves only
  horizontal lines.
- The minimal themes take the parameters of `theme_cowplot` plus `color`.

## Mistakes that do not raise

- **Line widths are points**: R's `line_size = 0.5` (mm) is `1` here;
  every `size` is about twice the R value.
- **R colour names fail in matplotlib** (`"grey85"` raises inside the
  draw, not at construction). Use hex: grey85 `#D9D9D9`, grey92 `#EBEBEB`.
- cowplot's plot background is transparent in R; here it stays white.
- No `plot_grid` / `ggdraw`; compose with plotnine's `p1 | p2`, `p1 / p2`.
