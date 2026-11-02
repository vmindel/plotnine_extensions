import numpy as np
from plotnine import aes, ggplot, labs, scale_x_continuous, theme_classic

from plotnine_extensions import geom_logo, logo_data

# 80 aligned binding sites around a TATA box, with some noise
rng = np.random.default_rng(0)
core = "GCTATAAAAGG"
sites = [
    "".join(b if rng.random() > 0.2 else rng.choice(list("ACGT")) for b in core)
    for _ in range(80)
]

p = (
    ggplot(logo_data(sites), aes("position", "height", label="letter"))
    + geom_logo()
    + scale_x_continuous(breaks=range(1, len(core) + 1))
    + theme_classic()
    + labs(y="bits")
)
