import numpy as np
import pandas as pd
from plotnine import aes, coord_flip, ggplot, theme, theme_classic

from plotnine_extensions import geom_raincloud

rng = np.random.default_rng(4)
df = pd.concat(
    [
        pd.DataFrame({"condition": c, "expression": rng.normal(m, s, n)})
        for c, m, s, n in [("WT", 0, 1, 200), ("KO", 1.2, 0.6, 120), ("Rescue", 0.4, 1.4, 80)]
    ]
)
df["condition"] = pd.Categorical(df["condition"], ["WT", "KO", "Rescue"])

p = (
    ggplot(df, aes("condition", "expression", fill="condition"))
    + geom_raincloud()
    + coord_flip()
    + theme_classic()
    + theme(legend_position="none")
)
