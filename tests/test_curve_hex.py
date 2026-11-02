import io

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path
from plotnine import aes, arrow, facet_wrap, ggplot

from plotnine_extensions import geom_curve, geom_hex, hex_bins
from plotnine_extensions.curve import _arrowstyle, _Bend
from plotnine_extensions.hex import _HEX


def built(p):
    fig = p.draw()
    FigureCanvasAgg(fig).draw()
    return fig


# geom_curve


def test_bend_control_point():
    path = _Bend(curvature=0.5, angle=90).connect((0, 0), (10, 0))
    # midway along, half the length to the right of travel (down for +x)
    np.testing.assert_allclose(path.vertices[1], [5, -5])
    path = _Bend(curvature=-0.2, angle=45).connect((0, 0), (10, 0))
    np.testing.assert_allclose(path.vertices[1], [2.5, 2])


def test_arrowstyle_mapping():
    assert _arrowstyle(None) == ("-", {})
    style, head = _arrowstyle(arrow(length=0.1, angle=30, ends="both", type="closed"))
    assert style == "<|-|>"
    assert head["head_length"] == pytest.approx(7.2)
    assert head["head_width"] == pytest.approx(7.2 * np.tan(np.radians(30)))
    assert _arrowstyle(arrow(ends="first"))[0] == "<-"


def test_curve_draws_one_patch_per_row():
    d = pd.DataFrame({"x": [0, 1, 2], "y": [0, 0, 0], "xend": [1, 2, 3], "yend": [1, 1, 1]})
    p = ggplot(d, aes("x", "y", xend="xend", yend="yend")) + geom_curve(arrow=arrow())
    fig = built(p)
    patches = [a for a in fig.axes[0].patches if isinstance(a, FancyArrowPatch)]
    assert len(patches) == 3


def test_curve_shrink_shortens_the_drawn_path():
    d = pd.DataFrame({"x": [0], "y": [0], "xend": [1], "yend": [0]})

    def length(**kw):
        fig = built(ggplot(d, aes("x", "y", xend="xend", yend="yend")) + geom_curve(curvature=0, **kw))
        (patch,) = [a for a in fig.axes[0].patches if isinstance(a, FancyArrowPatch)]
        v = patch.get_path().vertices
        return v[:, 0].max() - v[:, 0].min()

    assert length(shrink=20) < length()


def test_curve_angle_validated():
    with pytest.raises(ValueError):
        geom_curve(angle=0)
    with pytest.raises(ValueError):
        geom_curve(angle=200)


# geom_hex


@pytest.fixture
def points():
    rng = np.random.default_rng(0)
    return pd.DataFrame({"x": rng.normal(size=5000), "y": rng.normal(size=5000) * 3})


def test_hex_bins_conserve_counts_and_points_fall_in_their_hexagon(points):
    bw = (0.3, 0.8)
    out = hex_bins(points["x"], points["y"], bw)
    assert out["count"].sum() == len(points)

    # Assign each point again and check it lies inside its hexagon
    cells = {(round(x, 9), round(y, 9)) for x, y in zip(out["x"], out["y"])}
    assert len(cells) == len(out)
    for x, y in points.sample(500, random_state=1).to_numpy():
        one = hex_bins([x], [y], bw)
        cx, cy = one["x"].iloc[0], one["y"].iloc[0]
        hexagon = Path(np.column_stack([cx + _HEX[:, 0] * bw[0], cy + _HEX[:, 1] * bw[1] / 2]))
        assert hexagon.contains_point((x, y), radius=1e-9) or hexagon.contains_point(
            (x, y), radius=-1e-9
        )


def test_hex_bins_weights():
    out = hex_bins([0, 0.01, 5], [0, 0.01, 5], (1, 1), weight=[2, 3, 7])
    assert sorted(out["count"]) == [5, 7]


def test_stat_bin_hex_density_and_shared_grid_across_facets(points):
    points["g"] = np.arange(len(points)) % 2
    p = ggplot(points, aes("x", "y")) + geom_hex(bins=15) + facet_wrap("g")
    fig = built(p)
    assert len(fig.axes) == 2
    # Centres in both panels sit on one lattice: x offsets are multiples
    # of half a bin width
    bx = np.ptp(points["x"]) / 15
    tops = [
        np.array([path.vertices[0, 0] for path in ax.collections[0].get_paths()])
        for ax in fig.axes
    ]
    steps = (tops[1][:, None] - tops[0][None, :]) / (bx / 2)
    assert np.allclose(steps, np.round(steps), atol=1e-6)


def test_stat_bin_hex_binwidth_and_identity_stat():
    d = pd.DataFrame({"x": [0.0, 0.1, 2.0], "y": [0.0, 0.1, 2.0]})
    p = ggplot(d, aes("x", "y")) + geom_hex(binwidth=(1, 1))
    fig = built(p)
    assert len(fig.axes[0].collections[0].get_paths()) == 2
    pre = pd.DataFrame({"x": [0, 1], "y": [0, 1], "w": 1.0, "h": 1.0})
    mapped = ggplot(pre, aes("x", "y", width="w", height="h")) + geom_hex(stat="identity")
    assert len(built(mapped).axes[0].collections[0].get_paths()) == 2
    fixed = ggplot(pre, aes("x", "y")) + geom_hex(stat="identity", width=1, height=1)
    assert len(built(fixed).axes[0].collections[0].get_paths()) == 2
    with pytest.raises(Exception, match="width"):
        built(ggplot(pre, aes("x", "y")) + geom_hex(stat="identity"))


def test_hex_saves(points):
    buf = io.BytesIO()
    (ggplot(points, aes("x", "y")) + geom_hex()).save(
        buf, format="pdf", width=4, height=3, verbose=False
    )
    assert buf.getbuffer().nbytes > 0
