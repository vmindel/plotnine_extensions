# Sequence logos

```python
d = pnx.logo_data(data, alphabet=None, method="bits", sequence=None,
                  start=1, correction=True)
ggplot(d, aes("position", "height", label="letter")) + pnx.geom_logo()
```

`pnx.geom_logo(width=0.9, palette="auto", family=None, fontweight="bold")`
needs `x`, `y` and `label` mapped; it takes the long table from
`logo_data` (columns `position`, `letter`, `height`).

## logo_data inputs

| input | `alphabet` | typical `method` |
|---|---|---|
| list of aligned sequences (equal length) | inferred: DNA, RNA or protein | `"bits"`, `"probability"`, `"counts"` |
| DataFrame, positions x letters (columns are letters) | the columns | any |
| numpy array, positions x letters | **required**, e.g. `"ACGT"` (column order) | `"none"` for scores |

- `"bits"`: each letter's share of `log2(s) - H`. `correction=True`
  subtracts `(s - 1) / (2 ln 2 n)` (Schneider et al. 1986) when built from
  sequences; matrices have no `n`, so no correction.
- `"none"`: values as heights, may be negative (attributions, ISM).
- Contribution scores: pass the hypothetical-score matrix with
  `method="none", sequence=seq` to keep only the observed base at each
  position. Without `sequence`, every value is drawn: positives stack up,
  negatives down.
- Gaps `-` and `N` are ignored when counting.
- `start=` numbers the first position (e.g. genomic offset).

## Drawing

- Positive letters stack with the tallest on top; negative letters stack
  down from 0 with the largest magnitude lowest. Add
  `geom_hline(yintercept=0)` for signed logos.
- Colours: `palette="auto"` picks DNA/RNA/protein from the letters;
  `"dna"`, `"rna"`, `"protein"` (side-chain chemistry) or a
  `{letter: colour}` dict (`pnx.LOGO_PALETTES` holds the built-ins).
  Mapping `fill` overrides the palette and gives a legend.
- Letters are stretched to fill their box; narrow letters (I) become
  blocks.
- Facet over regions/models with a column added to the long table and
  `facet_wrap`.
- x ticks: use `scale_x_continuous(breaks=...)` for integer positions.
