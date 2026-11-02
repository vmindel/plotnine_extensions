"""Render the example figures into examples/out/."""

from pathlib import Path

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    facet_wrap,
    geom_point,
    geom_smooth,
    ggplot,
    scale_color_manual,
    theme_bw,
)

from plotnine_extensions import geom_label_repel, geom_text_repel, rasterise

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def volcano_data(n=3000, seed=1):
    rng = np.random.default_rng(seed)
    lfc = rng.normal(0, 1.2, n)
    nlp = np.abs(lfc * rng.uniform(0.5, 3, n))
    df = pd.DataFrame(
        {"lfc": lfc, "nlp": nlp, "gene": [f"G{i}" for i in range(n)]}
    )
    df["sig"] = (df["nlp"] > 5) & (df["lfc"].abs() > 2.5)
    # max_overlaps keeps earlier rows, so put the strongest hits first
    df = df.sort_values("nlp", ascending=False)
    df["lab"] = np.where(df["sig"], df["gene"], "")
    return df


def volcano():
    df = volcano_data()
    return (
        ggplot(df, aes("lfc", "nlp"))
        + rasterise(geom_point(aes(color="sig"), size=1), dpi=300)
        + geom_text_repel(aes(label="lab"), size=8, point_size=1)
        + scale_color_manual(["grey", "firebrick"])
        + theme_bw()
    )


def labels():
    df = volcano_data().head(16)
    df["panel"] = np.arange(len(df)) % 2
    return (
        ggplot(df, aes("lfc", "nlp", label="gene"))
        + geom_point(color="red")
        + geom_label_repel(fill="lightyellow", arrow={})
        + facet_wrap("panel")
    )


def raster_vs_vector():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": rng.normal(size=50_000)})
    df["y"] = df["x"] + rng.normal(size=len(df))
    return (
        ggplot(df, aes("x", "y"))
        + rasterise(geom_point(alpha=0.2, size=0.5), dpi=300)
        + geom_smooth(method="lm", color="red")
    )


if __name__ == "__main__":
    for name, p in {
        "volcano": volcano(),
        "labels": labels(),
        "rasterise": raster_vs_vector(),
    }.items():
        for ext in ("png", "pdf"):
            p.save(OUT / f"{name}.{ext}", width=6, height=5, dpi=150, verbose=False)
