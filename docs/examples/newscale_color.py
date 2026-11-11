import numpy as np
import pandas as pd
from plotnine import (
    aes,
    geom_point,
    geom_smooth,
    ggplot,
    labs,
    scale_color_cmap,
    scale_color_manual,
    theme_classic,
)

from plotnine_extensions import new_scale_color

# Promoter occupancy against expression in two conditions, GC per promoter
rng = np.random.default_rng(5)
n = 300
gc = rng.uniform(0.3, 0.7, 2 * n)
cond = np.repeat(["control", "heat shock"], n)
occupancy = rng.normal(0, 1, 2 * n) + 2 * (gc - 0.5)
slope = np.where(cond == "control", 0.4, 1.1)
df = pd.DataFrame(
    {
        "occupancy": occupancy,
        "expression": slope * occupancy + rng.normal(0, 0.7, 2 * n),
        "gc": gc,
        "condition": cond,
    }
)

p = (
    ggplot(df, aes("occupancy", "expression"))
    + geom_point(aes(color="gc"), size=1, alpha=0.7)
    + scale_color_cmap("viridis", name="GC")
    + new_scale_color()
    + geom_smooth(aes(color="condition"), method="lm", size=1.2)
    + scale_color_manual(["black", "firebrick"])
    + labs(x="occupancy (z)", y="log2 expression")
    + theme_classic()
)
