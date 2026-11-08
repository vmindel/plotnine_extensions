# Not shown in the docs; renders the side-by-side comparison of every theme
import numpy as np
import pandas as pd
from plotnine import aes, geom_point, ggplot, labs, theme

import plotnine_extensions as pnx

rng = np.random.default_rng(1)
df = pd.DataFrame({"x": rng.normal(size=60), "group": np.repeat(["a", "b", "c"], 20)})
df["y"] = df["x"] * 0.8 + rng.normal(0, 0.6, 60)

base = ggplot(df, aes("x", "y", color="group")) + geom_point(size=1.5) + labs(x="x", y="y")
THEMES = {
    "theme_pubr()": pnx.theme_pubr(base_size=10),
    "theme_pubr(border=True)": pnx.theme_pubr(base_size=10, border=True),
    "theme_pubclean()": pnx.theme_pubclean(base_size=10),
    "theme_classic2()": pnx.theme_classic2(base_size=10),
    "theme_cowplot()": pnx.theme_cowplot(font_size=10),
    "theme_minimal_grid()": pnx.theme_minimal_grid(font_size=10),
    "theme_minimal_hgrid()": pnx.theme_minimal_hgrid(font_size=10),
    "theme_minimal_vgrid()": pnx.theme_minimal_vgrid(font_size=10),
}
# A composition takes its size from the plots' figure_size, not from save()
plots = [base + labs(title=name) + th + theme(figure_size=(13, 6)) for name, th in THEMES.items()]
p = (plots[0] | plots[1] | plots[2] | plots[3]) / (plots[4] | plots[5] | plots[6] | plots[7])
