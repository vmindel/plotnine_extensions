import numpy as np
import pandas as pd
from plotnine import labs

from plotnine_extensions import ggcorrplot

# Ten tracks over 2,000 regions. The model recovers each track only in
# part and leaks the shared module signal into all of them, so predicted
# tracks correlate more with each other than the observed ones do.
rng = np.random.default_rng(5)
names = ["Msn2", "Msn4", "Hsf1", "Gis1", "Rap1", "Fhl1", "Ifh1", "Sfp1",
         "Reb1", "Abf1"]
module = [0, 0, 0, 0, 1, 1, 1, 1, 2, 3]
miss = np.linspace(0.3, 1.5, 10)  # how badly each track is predicted
shared = rng.normal(size=(2000, 4))
obs = pd.DataFrame(
    shared[:, module] + rng.normal(scale=1.0, size=(2000, 10)), columns=names
)
pred = (
    0.6 * obs
    + 0.5 * shared[:, module]
    + rng.normal(scale=miss, size=(2000, 10))
)

p = (
    ggcorrplot(
        obs.corr(),
        upper=pred.corr(),
        diag=obs.corrwith(pred),   # per-track accuracy, labelled by default
        hc_order=True,             # clustered on the observed matrix only
    )
    + labs(caption="lower: observed   upper: predicted   diagonal: obs vs pred")
)
