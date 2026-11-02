import pandas as pd
from plotnine import (
    aes,
    arrow,
    coord_fixed,
    geom_point,
    geom_text,
    ggplot,
    theme_void,
)

from plotnine_extensions import geom_curve

nodes = pd.DataFrame(
    {"name": ["TF", "enhancer", "promoter", "gene"], "x": [0, 1, 2, 3], "y": [1, 0, 1, 0]}
)
edges = pd.DataFrame(
    {"x": [0, 1, 2, 0], "y": [1, 0, 1, 1], "xend": [1, 2, 3, 2], "yend": [0, 1, 0, 1]}
)

p = (
    ggplot()
    + geom_curve(
        aes("x", "y", xend="xend", yend="yend"),
        data=edges,
        curvature=0.3,
        arrow=arrow(length=0.1, type="closed"),
        shrink=12,  # end the arrows at the edge of the nodes
        color="#555555",
    )
    + geom_point(aes("x", "y"), data=nodes, size=10, color="#3b6ea8")
    + geom_text(aes("x", "y", label="name"), data=nodes, nudge_y=-0.25, size=9)
    + coord_fixed(xlim=(-0.4, 3.4), ylim=(-0.5, 1.3))
    + theme_void()
)
