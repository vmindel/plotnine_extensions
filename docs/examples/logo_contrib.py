import numpy as np
from plotnine import aes, geom_hline, ggplot, labs, theme_classic

from plotnine_extensions import geom_logo, logo_data

# Contribution scores of a 40 bp window: hypothetical scores (positions x
# A, C, G, T) shown only for the bases of the actual sequence
rng = np.random.default_rng(1)
seq = "".join(rng.choice(list("ACGT"), 40))
seq = seq[:15] + "GATAAG" + seq[21:]
scores = rng.normal(0, 0.05, (40, 4))
scores[15:21] += 0.6  # a strong motif
scores[30:33] -= 0.4  # a repressive stretch

p = (
    ggplot(
        logo_data(scores, alphabet="ACGT", method="none", sequence=seq),
        aes("position", "height", label="letter"),
    )
    + geom_logo()
    + geom_hline(yintercept=0, size=0.3)
    + theme_classic()
    + labs(y="contribution")
)
