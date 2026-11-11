import numpy as np
import pandas as pd
from plotnine import (
    aes,
    geom_tile,
    ggplot,
    labs,
    scale_fill_cmap,
    scale_fill_manual,
    scale_x_continuous,
    theme_minimal,
)

from plotnine_extensions import new_scale_fill

# Signal of 40 regions over 30 bins around a summit, regions in 3 clusters
rng = np.random.default_rng(3)
cluster = np.repeat(["promoter", "enhancer", "other"], [15, 15, 10])
width = {"promoter": 3, "enhancer": 7, "other": 30}
bins = np.arange(-15, 15)
signal = pd.DataFrame(
    [
        (r, b, np.exp(-(b**2) / (2 * width[c] ** 2)) + rng.normal(0, 0.15))
        for r, c in enumerate(cluster)
        for b in bins
    ],
    columns=["region", "bin", "signal"],
)
annotation = pd.DataFrame(
    {"region": np.arange(len(cluster)), "bin": -18, "cluster": cluster}
)

p = (
    ggplot(mapping=aes("bin", "region"))
    + geom_tile(signal, aes(fill="signal"))
    + scale_fill_cmap("magma")
    + new_scale_fill()
    + geom_tile(annotation, aes(fill="cluster"), width=2)
    + scale_fill_manual(
        {"promoter": "#1b9e77", "enhancer": "#d95f02", "other": "#bbbbbb"}
    )
    + scale_x_continuous(breaks=[-15, 0, 14], labels=["-1.5 kb", "0", "+1.5 kb"])
    + labs(x="", y="region")
    + theme_minimal()
)
