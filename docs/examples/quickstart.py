from plotnine import aes, geom_point, ggplot
from plotnine.data import mtcars

from plotnine_extensions import geom_text_repel

p = (
    ggplot(mtcars, aes("wt", "mpg", label="name"))
    + geom_point(color="firebrick")
    + geom_text_repel(size=8)
)
