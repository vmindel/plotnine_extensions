import numpy as np
import pandas as pd
from plotnine import aes, geom_boxplot, geom_jitter, ggplot, theme_classic

from plotnine_extensions import stat_compare_means

rng = np.random.default_rng(5)
groups = ["WT", "KO", "Rescue", "Double"]
df = pd.concat(
    [pd.DataFrame({"genotype": g, "signal": rng.normal(m, 1, 25)}) for g, m in zip(groups, [0, 1.3, 0.3, 2])]
)
df["genotype"] = pd.Categorical(df["genotype"], groups)

# Every pair, Welch's t-test, Holm-corrected
p = (
    ggplot(df, aes("genotype", "signal"))
    + geom_boxplot(outlier_shape="", width=0.6)
    + geom_jitter(width=0.15, size=0.8, alpha=0.5)
    + stat_compare_means()
    + theme_classic()
)
