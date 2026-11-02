import numpy as np
import pandas as pd
from plotnine import aes, geom_line, ggplot, scale_x_continuous, theme

from plotnine_extensions import geom_text_repel

rng = np.random.default_rng(3)
genes = ["Pparg", "Cebpa", "Fabp4", "Adipoq", "Lep", "Klf15", "Srebf1"]
df = pd.concat(
    pd.DataFrame(
        {"hour": np.arange(25), "gene": g, "expr": rng.normal(0, 1, 25).cumsum()}
    )
    for g in genes
)
last = df[df["hour"] == df["hour"].max()]

p = (
    ggplot(df, aes("hour", "expr", color="gene"))
    + geom_line()
    + geom_text_repel(
        aes(label="gene"),
        data=last,
        nudge_x=2,
        direction="y",         # labels only move vertically
        xlim=(25.5, None),     # and stay right of the data
        size=8,
        segment_color="grey",
    )
    + scale_x_continuous(limits=(0, 31), breaks=range(0, 25, 6))
    + theme(legend_position="none")
)
