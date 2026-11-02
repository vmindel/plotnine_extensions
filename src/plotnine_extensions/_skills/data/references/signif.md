# Significance brackets

```python
pnx.stat_compare_means(mapping=None, data=None, comparisons=None,
                       ref_group=None, within=None, dodge_width=0.9,
                       method="t-test", paired=False, p_adjust="holm",
                       label_type="stars", hide_ns=False, step=0.08,
                       tip_length=0.02)
```

- Tests run on the **raw observations** of each group, separately in each
  facet panel. Add it to a plot whose `x` is the grouping and `y` the
  values (`ggplot(df, aes("genotype", "signal")) + geom_boxplot() + ...`).
- Which comparisons:
  - default: every pair of x categories;
  - `comparisons=[("WT", "KO"), ("WT", "Dbl")]`: by category name;
  - `ref_group="WT"`: every other group against one;
  - `within="fill"` with `aes(fill="genotype")` on the stat: compare
    levels of that aesthetic inside each x category (dodged plots).
    Brackets sit at the dodged positions for width 0.9, `geom_boxplot`'s
    and `position_dodge`'s default; set `dodge_width` otherwise.
- `method`: `"t-test"` = Welch (R's `t.test` default), `"student"` =
  equal variances, `"mann-whitney"` = Mann-Whitney U (R's two-sample
  `wilcox.test`). `paired=True`: paired t / Wilcoxon signed-rank, pairing
  by row order within each group (groups must be the same size and in the
  same order).
- `p_adjust="holm"` **by default** (also `"bh"`, `"bonferroni"`, `None`),
  across the comparisons of a panel; labels then read `p.adj`. ggpubr's
  brackets are uncorrected by default, so numbers differ from R unless
  `p_adjust=None`.
- `label_type="stars"`: `ns` > 0.05, `*` <= 0.05, `**` <= 0.01, `***` <=
  0.001, `****` <= 0.0001; `"p"` prints the value. **Not `label=`**: that
  is the text aesthetic and raises `TypeError`.
- `hide_ns=True` drops non-significant brackets.
- Brackets stack automatically (narrowest first, above the data they
  span); `step` and `tip_length` are fractions of the y range.
- Categories need at least 2 observations each; comparisons with fewer
  are skipped.

## Your own p-values

```python
results = pd.DataFrame({"start": ["WT", "WT"], "end": ["KO", "Dbl"],
                        "height": [4.2, 5.0], "text": ["padj = 0.003", "***"]})
p + pnx.geom_bracket(aes(xmin="start", xmax="end", y="height", label="text"),
                     data=results, inherit_aes=False)
```

`xmin`/`xmax` may be category names. `inherit_aes=False` keeps the plot's
`x`/`y` mapping from leaking in. `pnx.p_adjust(p, method)` and
`pnx.format_p(p, label_type)` give the same corrections and labels for
your own tables.
