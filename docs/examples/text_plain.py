from plotnine import aes, geom_point, geom_text, ggplot
from plotnine.data import mtcars

p = (
    ggplot(mtcars, aes("wt", "mpg", label="name"))
    + geom_point(color="firebrick")
    + geom_text(size=8)
)
