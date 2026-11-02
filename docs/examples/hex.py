import numpy as np
import pandas as pd
from plotnine import aes, ggplot, labs, scale_fill_cmap, theme_bw

from plotnine_extensions import geom_hex

rng = np.random.default_rng(3)
cells = pd.DataFrame({"atac": rng.normal(size=30_000)})
cells["rna"] = 0.7 * cells["atac"] + rng.normal(0, 0.7, len(cells))

p = (
    ggplot(cells, aes("atac", "rna"))
    + geom_hex(bins=40)
    + scale_fill_cmap("viridis")
    + theme_bw()
    + labs(x="ATAC (z-score)", y="RNA (z-score)")
)
