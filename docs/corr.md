# Correlation matrices

`ggcorrplot` draws a correlation matrix as a heatmap, after R's
ggcorrplot. It takes the matrix, not the data: compute it first with
`df.corr()` (any method), and pass p-values from `cor_pmat` to mark or
hide the insignificant cells. The result is an ordinary `ggplot`, so
themes, scales and further layers add on with `+`.

## Triangle, clustering, labels

```python
--8<-- "examples/corr_basic.py"
```

![Lower triangle, clustered, with coefficients](img/corr_basic.png)

`hc_order=True` orders the variables by hierarchical clustering on
(1 − r) / 2, so strongly anticorrelated variables count as far apart, not
as a module. `hc_method` picks the linkage (`"complete"` by default).

## Significance

```python
--8<-- "examples/corr_pmat.py"
```

![Circles, insignificant cells crossed](img/corr_pmat.png)

`cor_pmat` tests every pair of columns with `scipy.stats` (Pearson,
Spearman or Kendall), using the rows where both are present. Cells with
p above `sig_level` (0.05) get a cross, or with `insig="blank"` are not
drawn. An n-variable matrix is n(n − 1) / 2 tests, so pass
`adjust="holm"` or `"bh"` unless you have a reason not to; R's
`cor_pmat` does not adjust.

## Arguments

| | |
|---|---|
| `method="square"` | Tiles; `"circle"` draws circles with area proportional to \|r\| |
| `type="full"` | Also `"lower"`, `"upper"` |
| `show_diag=None` | Diagonal drawn for `"full"` only, unless set |
| `hc_order=False`, `hc_method="complete"` | Cluster the variables |
| `lab=False`, `lab_size=11`, `lab_col`, `digits=2` | Coefficients in the cells |
| `p_mat=None`, `sig_level=0.05`, `insig="pch"` | Mark (`"pch"`) or drop (`"blank"`) insignificant cells |
| `pch="x"`, `pch_col`, `pch_cex=5` | The mark: a matplotlib marker and its `geom_point` size |
| `colors=("blue", "white", "red")` | Fill at −1, 0 and 1 |
| `outline_color="gray"` | Tile border or circle outline |
| `ggtheme=theme_minimal` | Base theme, a class or an instance |
| `tl_cex=12`, `tl_col`, `tl_srt=45` | Tick label size (points), colour, x rotation |
| `title`, `show_legend`, `legend_title="Corr"` | |

The plot's data has one row per drawn cell with columns `var1` (x),
`var2` (y), `value`, `abs_corr` and, with `p_mat`, `pvalue`, for layers
of your own.

## Differences from R

- **Argument names swap dots for underscores**: `hc.order` is
  `hc_order`, `p.mat` is `p_mat`, `tl.cex` is `tl_cex`.
- **`lab_size` is in points.** R's `lab_size = 4` (mm) is about 11.
- **`pch` is a matplotlib marker**, not an R symbol number: R's default
  `pch = 4` is `"x"`.
- **Circle area is proportional to \|r\|, from 0 to 1.** ggcorrplot
  rescales circle size to the range of the matrix, so the weakest
  correlation in a matrix still draws a mid-sized circle and sizes do
  not compare across figures.
- **Insignificant cells with `insig="blank"` are not drawn at all**,
  labels included.
- **Clustering uses scipy.** The tree matches R's `hclust` for the same
  linkage, but leaves can come out in a different left-right order.
  `hc_method="ward.D2"` maps to scipy's `"ward"` and `"mcquitty"` to
  `"weighted"`; R's `"ward.D"` has no scipy counterpart.
- **Raw data is refused.** A matrix with values outside [−1, 1] raises
  an error instead of being plotted as if it were correlations.
- Labels keep trailing zeros (`0.50`, not `0.5`).
- Not included: `as.is`.
