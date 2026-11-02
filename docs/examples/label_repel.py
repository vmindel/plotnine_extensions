from plotnine import aes, geom_point, ggplot
from plotnine.data import mtcars

from plotnine_extensions import geom_label_repel

p = (
    ggplot(mtcars, aes("wt", "mpg", label="name", fill="factor(cyl)"))
    + geom_point()
    + geom_label_repel(
        color="white", size=7, boxcolor="none", segment_color="grey"
    )
)
