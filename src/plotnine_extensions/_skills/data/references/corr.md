# Correlation matrices (ggcorrplot)

```python
corr = df.corr()                                  # or method="spearman"
p = pnx.cor_pmat(df, method="pearson", adjust="holm")
pnx.ggcorrplot(corr, method="square", type="lower", hc_order=True,
               hc_method="complete", lab=True, lab_size=8, digits=2,
               p_mat=p, sig_level=0.05, insig="pch")
```

- Takes the **correlation matrix**, not the data. Values outside [-1, 1]
  raise `ValueError`; pass `df.corr()`.
- Returns a plain `ggplot`: add `+ ggtitle(...)`, `+ theme(...)` etc.
  The plot data has `var1` (x), `var2` (y), `value`, `abs_corr`, and
  `pvalue` when `p_mat` is given.
- `type`: `"full"`, `"lower"`, `"upper"`. `show_diag` defaults to `True`
  only for `"full"`.
- `method="circle"`: circle area proportional to |r| on a fixed 0-1
  scale (unlike R, which rescales to the data range).
- `hc_order=True` clusters on (1 - r) / 2: anticorrelated variables are
  far apart. `hc_method` accepts scipy names and R's `"ward.D2"`,
  `"mcquitty"`; `"ward.D"` raises. Leaf order can differ from R.
- `p_mat` as a DataFrame is aligned to `corr` by labels; an array must
  have the same shape and order. Reordered together with `hc_order`.
- `insig="pch"` overlays `pch` (matplotlib marker, default `"x"`) of size
  `pch_cex`; `insig="blank"` drops the cell and its label.
- `cor_pmat` defaults to **no multiple-testing correction**, as in R. A
  matrix of n variables is n(n - 1) / 2 tests: use `adjust="holm"` or
  `"bh"`. Pairs use rows where both columns are present.
- Units: `lab_size` and `tl_cex` are points (R's `lab_size = 4` is about
  11). `tl_srt` rotates the x labels; `tl_col` colours them.
- Other arguments: `colors=("blue", "white", "red")` for -1/0/1,
  `outline_color="gray"`, `ggtheme=theme_minimal` (class or instance),
  `title`, `show_legend`, `legend_title="Corr"`, `lab_col`, `pch_col`.
- Many variables: shrink `lab_size` and `tl_cex`, or drop `lab`; circle
  sizes are in points, so enlarge the figure rather than expecting them
  to shrink.
