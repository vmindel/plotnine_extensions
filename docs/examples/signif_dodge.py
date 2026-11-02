import numpy as np
import pandas as pd
from plotnine import aes, geom_boxplot, ggplot, theme_classic

from plotnine_extensions import stat_compare_means

rng = np.random.default_rng(6)
df = pd.concat(
    [
        pd.DataFrame({"tissue": t, "genotype": g, "expression": rng.normal(m, 1, 25)})
        for t, effect in [("liver", 1.0), ("muscle", 0.2), ("brain", 0.6)]
        for g, m in [("WT", 0), ("KO", effect)]
    ]
)
df["genotype"] = pd.Categorical(df["genotype"], ["WT", "KO"])

# Compare genotypes within each tissue
p = (
    ggplot(df, aes("tissue", "expression", fill="genotype"))
    + geom_boxplot()
    + stat_compare_means(aes(fill="genotype"), within="fill", label_type="p")
    + theme_classic()
)
