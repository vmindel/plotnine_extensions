import numpy as np
from plotnine import aes, geom_point, ggplot, scale_y_continuous
from plotnine.data import mtcars

from plotnine_extensions import geom_text_repel

df = mtcars.assign(lab=np.where(mtcars["wt"] < 2.5, mtcars["name"], ""))

p = (
    ggplot(df, aes("wt", "mpg", label="lab"))
    + geom_point()
    + geom_text_repel(
        nudge_y=8,              # start every label 8 mpg higher...
        direction="x",          # ...then only spread them sideways
        ylim=(36, None),        # and keep them in a band at the top
        segment_color="grey",
        segment_size=0.4,
        arrow={"arrowstyle": "-|>", "mutation_scale": 6},
        angle=90,
        size=7,
    )
    + scale_y_continuous(limits=(10, 46))
)
