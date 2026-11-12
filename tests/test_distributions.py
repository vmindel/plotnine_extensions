import io
import warnings

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.colors import to_hex
from matplotlib.text import Text
from plotnine import aes, coord_flip, geom_point, geom_violin, ggplot

from plotnine_extensions import (
    geom_raincloud,
    position_jitternudge,
    stat_halfeye,
    stat_pointinterval,
)


@pytest.fixture
def df():
    rng = np.random.default_rng(3)
    return pd.concat(
        [
            pd.DataFrame({"g": "a", "y": rng.normal(0, 1, 300)}),
            pd.DataFrame({"g": "b", "y": rng.normal(2, 0.5, 200)}),
        ],
        ignore_index=True,
    )


def built(p):
    fig = p.draw()
    FigureCanvasAgg(fig).draw()
    return fig


def interval_lines(fig):
    (lc,) = [c for c in fig.axes[0].collections if isinstance(c, LineCollection)]
    return lc


def test_pointinterval_values(df):
    fig = built(ggplot(df, aes("g", "y")) + stat_pointinterval())
    lc = interval_lines(fig)
    segs = lc.get_segments()
    assert len(segs) == 4  # 2 groups x 2 widths
    a = df.query("g == 'a'")["y"].to_numpy()
    lo95, hi95 = np.quantile(a, [0.025, 0.975])
    lo66, hi66 = np.quantile(a, [0.17, 0.83])
    spans = {tuple(np.round(sorted([s[0][1], s[1][1]]), 6)) for s in segs if s[0][0] == 1}
    assert spans == {tuple(np.round([lo95, hi95], 6)), tuple(np.round([lo66, hi66], 6))}
    # the narrower interval is drawn thicker
    widths = lc.get_linewidths()
    lengths = [abs(s[1][1] - s[0][1]) for s in segs]
    assert widths[int(np.argmin(lengths))] > widths[int(np.argmax(lengths))]
    # one point per group, at the median
    pts = fig.axes[0].collections[-1].get_offsets()
    assert len(pts) == 2
    assert np.median(a) in np.round(pts[:, 1], 12) or np.isclose(pts[:, 1], np.median(a)).any()


def test_pointinterval_mean_and_validation(df):
    fig = built(ggplot(df, aes("g", "y")) + stat_pointinterval(point="mean", widths=[0.5]))
    pts = fig.axes[0].collections[-1].get_offsets()
    assert np.isclose(pts[:, 1], df.query("g == 'b'")["y"].mean()).any()
    with pytest.raises(ValueError):
        stat_pointinterval(point="mode")
    with pytest.raises(ValueError):
        stat_pointinterval(widths=[1.2])


def test_pointinterval_with_coord_flip(df):
    fig = built(ggplot(df, aes("g", "y")) + stat_pointinterval() + coord_flip())
    for seg in interval_lines(fig).get_segments():
        assert seg[0][1] == seg[1][1]  # horizontal


def test_jitternudge_shifts_and_is_reproducible(df):
    def xs(seed):
        fig = built(
            ggplot(df, aes("g", "y"))
            + geom_point(position=position_jitternudge(width=0.05, nudge_x=-0.3, random_state=seed))
        )
        return fig.axes[0].collections[0].get_offsets()[:, 0]

    x = xs(1)
    base = np.where(df["g"] == "a", 1, 2)
    assert np.all(np.abs(x - (base - 0.3)) <= 0.05 + 1e-9)
    np.testing.assert_array_equal(x, xs(1))


def test_halfeye_and_raincloud_layers(df):
    he = stat_halfeye()
    assert len(he) == 2 and isinstance(he[0], geom_violin)
    assert len(geom_raincloud()) == 3
    assert len(geom_raincloud(box_width=0)) == 2
    mapped = geom_raincloud(aes(fill="g"))
    assert "fill" not in mapped[0].aes_params


def test_render_without_warnings(df):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", message=".*inplace.*")
        for layers in (stat_halfeye(), geom_raincloud(aes(fill="g")), stat_halfeye(nudge=0.1)):
            p = ggplot(df, aes("g", "y")) + layers
            buf = io.BytesIO()
            p.save(buf, format="png", width=4, height=3, dpi=50, verbose=False)


def legend_artists(fig):
    """
    Artists of the legend keys (the legend is the figure's only OffsetBox)
    """
    from matplotlib.lines import Line2D
    from matplotlib.offsetbox import DrawingArea

    return [
        a
        for da in fig.findobj(DrawingArea)
        for a in da.get_children()
        if isinstance(a, Line2D)
    ]


@pytest.mark.parametrize(
    "layers",
    [
        lambda m: stat_halfeye(m),
        lambda m: stat_pointinterval(m),
        lambda m: geom_raincloud(m),
    ],
    ids=["halfeye", "pointinterval", "raincloud"],
)
@pytest.mark.parametrize("ae", ["fill", "color"])
def test_legend_with_mapped_aesthetic(df, layers, ae):
    # The point-interval legend used to read a size column it never has
    p = ggplot(df, aes("g", "y")) + layers(aes(**{ae: "g"}))
    fig = built(p)
    labels = {t.get_text() for t in fig.findobj(Text)}
    assert {"g", "a", "b"} <= labels
    assert legend_artists(fig)


def test_pointinterval_legend_key(df):
    p = ggplot(df, aes("g", "y")) + stat_pointinterval(
        aes(fill="g"), interval_size=(0.5, 2), point_size=3
    )
    keys = legend_artists(built(p))
    lines = [k for k in keys if k.get_marker() in (None, "None", "")]
    points = [k for k in keys if k.get_marker() == "o"]
    assert len(lines) == len(points) == 2  # one per level
    # the key's line is the narrowest interval, which is drawn thickest
    from plotnine._utils import SIZE_FACTOR

    assert lines[0].get_linewidth() == pytest.approx(2 * SIZE_FACTOR)
    fills = {to_hex(k.get_markerfacecolor()) for k in points}
    assert len(fills) == 2
