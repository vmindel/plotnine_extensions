import numpy as np
import pandas as pd
from plotnine import (
    aes,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme_bw,
)

from plotnine_extensions import geom_text_repel, rasterise

rng = np.random.default_rng(1)
n = 3000
lfc = rng.normal(0, 1.2, n)
df = pd.DataFrame(
    {
        "log2fc": lfc,
        "nlog10p": np.abs(lfc * rng.uniform(0.5, 3, n)),
        "gene": [f"G{i}" for i in range(n)],
    }
)
df["hit"] = (df["nlog10p"] > 5) & (df["log2fc"].abs() > 2.5)

# Labels that cannot be placed are dropped last-row-first,
# so put the strongest hits at the top.
df = df.sort_values("nlog10p", ascending=False)
df["lab"] = np.where(df["hit"], df["gene"], "")

p = (
    ggplot(df, aes("log2fc", "nlog10p"))
    + rasterise(geom_point(aes(color="hit"), size=1), dpi=300)
    + geom_text_repel(aes(label="lab"), size=7, point_size=1)
    + scale_color_manual(["grey", "firebrick"], guide=None)
    + labs(x="log2 fold change", y="-log10 p")
    + theme_bw()
)
