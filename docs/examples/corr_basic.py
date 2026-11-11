import numpy as np
import pandas as pd

from plotnine_extensions import ggcorrplot

# Binding signal of ten factors over 500 regions, in two co-bound modules
rng = np.random.default_rng(7)
mod_a, mod_b = rng.normal(size=(2, 500))
factors = {
    "Msn2": mod_a, "Msn4": mod_a, "Hsf1": 0.6 * mod_a, "Gis1": 0.4 * mod_a,
    "Rap1": mod_b, "Fhl1": mod_b, "Ifh1": 0.8 * mod_b, "Sfp1": 0.5 * mod_b,
    "Reb1": -0.3 * mod_b, "Abf1": 0 * mod_a,
}
df = pd.DataFrame(
    {k: v + rng.normal(scale=0.6, size=500) for k, v in factors.items()}
)

p = ggcorrplot(df.corr(method="spearman"), type="lower", hc_order=True,
               lab=True, lab_size=8)
