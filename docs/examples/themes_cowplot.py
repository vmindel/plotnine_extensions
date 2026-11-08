import numpy as np
import pandas as pd
from plotnine import aes, geom_col, ggplot, labs, position_dodge, scale_y_continuous

from plotnine_extensions import theme_minimal_hgrid

df = pd.DataFrame(
    {
        "motif": np.repeat(["CTCF", "AP-1", "SP/KLF", "ETS"], 2),
        "set": ["peaks", "background"] * 4,
        "frac": [0.42, 0.06, 0.31, 0.11, 0.55, 0.38, 0.27, 0.19],
    }
)

p = (
    ggplot(df, aes("motif", "frac", fill="set"))
    + geom_col(position=position_dodge(width=0.8), width=0.75)
    + scale_y_continuous(expand=(0, 0), limits=(0, 0.6))
    + labs(x="", y="Fraction with motif", fill="", title="Motif enrichment")
    + theme_minimal_hgrid(font_size=12)
)
