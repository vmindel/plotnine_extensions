"""
Run every docs example and save the figures the docs show

Each file in docs/examples defines a plot `p`. The docs include the same
files verbatim, so a figure always comes from the code next to it.

    python docs/gen_figures.py
"""

import io
import runpy
import warnings
from pathlib import Path

from plotnine.exceptions import PlotnineWarning

HERE = Path(__file__).parent
EXAMPLES = HERE / "examples"
IMG = HERE / "img"
GENERATED = HERE / "generated"

SIZES = {
    "logo_bits": (6, 2.4),
    "logo_contrib": (7, 2.4),
    "logo_ism": (7, 2.6),
    "curve": (6, 3),
    "hex": (5.5, 4.5),
    "halfeye": (5, 4),
    "raincloud": (5.5, 4),
    "signif_pairs": (5, 4.5),
    "signif_ref": (5, 4.2),
    "signif_dodge": (5.5, 4),
    "signif_manual": (5, 4.2),
    "segments": (6, 4.5),
    "line_ends": (6, 4),
    "volcano": (6, 5),
    "themes_pubr": (4.5, 4.2),
    "themes_cowplot": (5.5, 4),
    "corr_basic": (5.5, 4.8),
    "corr_pmat": (5, 4.5),
    "corr_obs_pred": (5.5, 5),
    "newscale_heatmap": (5, 4.5),
    "newscale_color": (5.5, 4),
    # a composition: its size comes from figure_size inside the example
    "themes_gallery": (13, 6),
}


def run(name):
    return runpy.run_path(str(EXAMPLES / f"{name}.py"))["p"]


def pdf_kb(p, width, height):
    buf = io.BytesIO()
    p.save(buf, format="pdf", width=width, height=height, verbose=False)
    return buf.getbuffer().nbytes / 1024


def size_table():
    from plotnine import aes, geom_point, geom_smooth, ggplot

    from plotnine_extensions import rasterise

    df = runpy.run_path(str(EXAMPLES / "rasterise_basic.py"))["df"]
    vector = (
        ggplot(df, aes("x", "y"))
        + geom_point(alpha=0.1, size=0.3)
        + geom_smooth(method="lm", color="firebrick")
    )
    rows = [("all vector", pdf_kb(vector, 5, 4))]
    for dpi in (150, 300, 600):
        q = rasterise(vector, dpi=dpi, layers=["point"])
        rows.append((f"`rasterise(..., dpi={dpi})`", pdf_kb(q, 5, 4)))
    lines = ["| 100,000 points + smooth, 5 x 4 in | PDF size |", "|---|---|"]
    lines += [f"| {label} | {kb / 1024:.2f} MB |" for label, kb in rows]
    return "\n".join(lines) + "\n"


def main():
    IMG.mkdir(exist_ok=True)
    GENERATED.mkdir(exist_ok=True)
    for path in sorted(EXAMPLES.glob("*.py")):
        name = path.stem
        width, height = SIZES.get(name, (6, 4.5))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PlotnineWarning)
            run(name).save(
                IMG / f"{name}.png", width=width, height=height, dpi=130,
                verbose=False,
            )
        print(f"docs/img/{name}.png")
    (GENERATED / "raster_sizes.md").write_text(size_table())
    print("docs/generated/raster_sizes.md")


if __name__ == "__main__":
    main()
