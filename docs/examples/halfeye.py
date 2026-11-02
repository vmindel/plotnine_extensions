import numpy as np
import pandas as pd
from plotnine import aes, ggplot, theme_classic

from plotnine_extensions import stat_halfeye

rng = np.random.default_rng(4)
df = pd.concat(
    [
        pd.DataFrame({"condition": c, "expression": rng.normal(m, s, n)})
        for c, m, s, n in [("WT", 0, 1, 200), ("KO", 1.2, 0.6, 120), ("Rescue", 0.4, 1.4, 80)]
    ]
)
df["condition"] = pd.Categorical(df["condition"], ["WT", "KO", "Rescue"])

# Density, median, and 66% (thick) and 95% (thin) intervals
p = (
    ggplot(df, aes("condition", "expression"))
    + stat_halfeye()
    + theme_classic()
)
