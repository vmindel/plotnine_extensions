import numpy as np
from plotnine import aes, geom_hline, ggplot, labs, theme_classic

from plotnine_extensions import geom_logo, logo_data

# In silico mutagenesis: effect of every possible base at every position,
# positive and negative, stacked above and below zero
rng = np.random.default_rng(2)
ism = rng.normal(0, 0.1, (25, 4))
ism[8:13] *= 8

p = (
    ggplot(
        logo_data(ism, alphabet="ACGT", method="none"),
        aes("position", "height", label="letter"),
    )
    + geom_logo()
    + geom_hline(yintercept=0, size=0.3)
    + theme_classic()
    + labs(y="ISM effect")
)
