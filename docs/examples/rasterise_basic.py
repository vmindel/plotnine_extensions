import numpy as np
import pandas as pd
from plotnine import aes, geom_point, geom_smooth, ggplot

from plotnine_extensions import rasterise

rng = np.random.default_rng(0)
df = pd.DataFrame({"x": rng.normal(size=100_000)})
df["y"] = df["x"] + rng.normal(size=len(df))

p = (
    ggplot(df, aes("x", "y"))
    + rasterise(geom_point(alpha=0.1, size=0.3), dpi=300)
    + geom_smooth(method="lm", color="firebrick")  # stays vector
)
