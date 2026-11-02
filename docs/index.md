# plotnine-extensions

ggplot2's strength is its extension ecosystem. This package brings the
most-used pieces of it to [plotnine](https://plotnine.org). Everything is
an ordinary plotnine layer: import it and add it to a plot with `+`.

| | ggplot2 counterpart | |
|---|---|---|
| [`geom_text_repel`, `geom_label_repel`](repel.md) | ggrepel | Labels that move off each other and off the data, with leader lines |
| [`rasterise`](rasterise.md) | ggrastr | One layer as a bitmap at its own dpi inside PDF/SVG output |

## Install

```bash
pip install git+https://github.com/vmindel/plotnine_extensions
```

It needs plotnine 0.15 or later and is tested against 0.15.8 and
plotnine's development branch.

## Quick start

```python
--8<-- "examples/quickstart.py"
```

![Repelled labels on mtcars](img/quickstart.png)

A genomics-flavoured example uses both features at once: 3,000 points
rasterised, so the PDF stays small, and only the hits labelled.

```python
--8<-- "examples/volcano.py"
```

![Volcano plot](img/volcano.png)
