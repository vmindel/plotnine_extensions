import numpy as np
import pandas as pd
from plotnine import aes, geom_boxplot, geom_jitter, ggplot, labs

from plotnine_extensions import rotate_x_text, stat_compare_means, theme_pubr

rng = np.random.default_rng(3)
groups = ["WT", "ΔIDR", "IDR swap", "DBD only"]
df = pd.concat(
    [pd.DataFrame({"construct": g, "occupancy": rng.normal(m, 0.8, 30)}) for g, m in zip(groups, [2, 0.6, 1.8, 0.2])]
)
df["construct"] = pd.Categorical(df["construct"], groups)

p = (
    ggplot(df, aes("construct", "occupancy", fill="construct"))
    + geom_boxplot(outlier_shape="", width=0.6)
    + geom_jitter(width=0.15, size=0.8, alpha=0.5)
    + stat_compare_means(ref_group="WT")
    + labs(x="", y="log2 occupancy")
    + theme_pubr(legend="none")
    + rotate_x_text(45)
)
