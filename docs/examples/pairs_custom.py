import numpy as np
import pandas as pd
from plotnine import geom_point, geom_smooth, theme_bw

from plotnine_extensions import ggpairs, rasterise

# Three replicates of a ChEC-seq profile over 5,000 bins, and input
rng = np.random.default_rng(5)
true = rng.gamma(1.5, size=5000)
df = pd.DataFrame({
    f"rep{i}": np.log2(1 + rng.poisson(20 * true)) for i in (1, 2, 3)
})
df["input"] = np.log2(1 + rng.poisson(20, size=5000))

p = ggpairs(
    df,
    lower=[geom_point(alpha=0.1, size=0.4),
           geom_smooth(method="lowess", color="firebrick")],
    diag="hist",
    method="spearman",
    labels={"input": "input (log2)"},
) + theme_bw()
p = rasterise(p, layers=["point"], dpi=300)
