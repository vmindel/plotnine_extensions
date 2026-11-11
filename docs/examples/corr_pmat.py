import numpy as np
import pandas as pd

from plotnine_extensions import cor_pmat, ggcorrplot

# Eight weakly coupled measurements on 60 samples
rng = np.random.default_rng(11)
x = rng.normal(size=(60, 8))
x[:, 1] += 0.8 * x[:, 0]
x[:, 2] -= 0.6 * x[:, 0]
x[:, 5] += 0.5 * x[:, 4]
x[:, 7] += 0.4 * x[:, 6]
df = pd.DataFrame(x, columns=[f"m{i}" for i in range(1, 9)])

p = ggcorrplot(
    df.corr(),
    method="circle",
    p_mat=cor_pmat(df, adjust="holm"),  # 28 tests; R's default is unadjusted
)
