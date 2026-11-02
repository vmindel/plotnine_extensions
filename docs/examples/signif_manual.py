import numpy as np
import pandas as pd
from plotnine import aes, geom_boxplot, ggplot, theme_classic

from plotnine_extensions import geom_bracket

rng = np.random.default_rng(5)
groups = ["WT", "KO", "Rescue", "Double"]
df = pd.concat(
    [pd.DataFrame({"genotype": g, "signal": rng.normal(m, 1, 25)}) for g, m in zip(groups, [0, 1.3, 0.3, 2])]
)
df["genotype"] = pd.Categorical(df["genotype"], groups)

# p-values computed elsewhere (e.g. a mixed model, DESeq2, limma)
results = pd.DataFrame(
    {
        "start": ["WT", "WT"],
        "end": ["KO", "Double"],
        "height": [4.2, 5.0],
        "text": ["padj = 0.003", "padj = 1.2e-6"],
    }
)

p = (
    ggplot(df, aes("genotype", "signal"))
    + geom_boxplot(width=0.6)
    + geom_bracket(
        aes(xmin="start", xmax="end", y="height", label="text"),
        data=results,
        inherit_aes=False,
    )
    + theme_classic()
)
