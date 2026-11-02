import numpy as np
import pandas as pd
from plotnine import aes, geom_boxplot, ggplot, theme_classic

from plotnine_extensions import stat_compare_means

rng = np.random.default_rng(5)
groups = ["WT", "KO", "Rescue", "Double"]
df = pd.concat(
    [pd.DataFrame({"genotype": g, "signal": rng.normal(m, 1, 25)}) for g, m in zip(groups, [0, 1.3, 0.3, 2])]
)
df["genotype"] = pd.Categorical(df["genotype"], groups)

# Each mutant against wild type, Mann-Whitney, p-values shown
p = (
    ggplot(df, aes("genotype", "signal"))
    + geom_boxplot(width=0.6)
    + stat_compare_means(ref_group="WT", method="mann-whitney", label_type="p")
    + theme_classic()
)
