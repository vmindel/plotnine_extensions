import numpy as np
import pandas as pd
from plotnine import theme_bw

from plotnine_extensions import ggpairs

# Signal of four factors over 300 promoters in three chromatin classes
rng = np.random.default_rng(3)
cls = np.repeat(["active", "poised", "silent"], 100)
shift = pd.Series(cls).map({"active": 2.0, "poised": 1.0, "silent": 0.0})
msn2 = shift.to_numpy() + rng.normal(scale=0.7, size=300)
df = pd.DataFrame({
    "Msn2": msn2,
    "Msn4": 0.8 * msn2 + rng.normal(scale=0.5, size=300),
    "Rap1": rng.normal(size=300) + 0.5 * shift.to_numpy(),
    "Reb1": rng.gamma(2, size=300),
    "class": cls,
})

p = ggpairs(df, color="class") + theme_bw()
