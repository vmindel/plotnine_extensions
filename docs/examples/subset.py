import numpy as np
from plotnine import aes, geom_point, ggplot
from plotnine.data import mtcars

from plotnine_extensions import geom_text_repel

# Blank the labels you do not want instead of dropping the rows:
# unlabelled points still keep labels off themselves.
df = mtcars.assign(
    lab=np.where((mtcars["mpg"] > 25) | (mtcars["wt"] > 5), mtcars["name"], "")
)

p = (
    ggplot(df, aes("wt", "mpg", label="lab"))
    + geom_point(color="grey")
    + geom_point(df[df["lab"] != ""], color="firebrick")
    + geom_text_repel(size=8)
)
