import pickle
import warnings

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest
from matplotlib.text import Text
from plotnine import (
    aes,
    after_stat,
    facet_wrap,
    geom_bin_2d,
    geom_boxplot,
    geom_line,
    geom_point,
    geom_tile,
    ggplot,
    guide_legend,
    guides,
    labs,
    position_jitterdodge,
    scale_color_manual,
    scale_fill_gradient,
    scale_fill_manual,
)
from plotnine.exceptions import PlotnineWarning
from plotnine.layer import layer

import plotnine_extensions as pnx


@pytest.fixture
def df():
    rng = np.random.default_rng(0)
    n = 60
    return pd.DataFrame(
        {
            "x": rng.normal(size=n),
            "y": rng.normal(size=n),
            "g": rng.choice(["a", "b"], n),
            "h": rng.choice(["p", "q", "r"], n),
            "v": rng.uniform(size=n),
        }
    )


def texts(fig):
    return {t.get_text() for t in fig.findobj(Text)}


def built(p):
    """
    Layers and scales of the last p.draw()

    plotnine 0.15 builds the plot in place; later versions build a copy.
    """
    return getattr(p, "built", None) or p._build_objs


def legends(p):
    """
    {title: [layer indices drawn in that legend]} after p.draw()
    """
    layers = built(p).layers
    out = {}
    for _, g in p.guides._lookup.values():
        if not hasattr(g, "key"):  # not trained, so not drawn
            continue
        out[g.title] = [
            i for i, lyr in enumerate(layers) if g.legend_aesthetics(lyr)
        ]
    return out


def draw(p):
    # plotnine's own warnings (e.g. "Cannot generate legend") fail the
    # test; deprecation notices from pandas or plotnine internals do not
    with warnings.catch_warnings():
        warnings.simplefilter("error", PlotnineWarning)
        return p.draw()


def test_two_fill_scales(df):
    grid = pd.DataFrame(
        {"x": [0, 1, 0, 1], "y": [0, 0, 1, 1], "z": [1, 2, 3, 4]}
    )
    p = (
        ggplot(mapping=aes("x", "y"))
        + geom_tile(grid, aes(fill="z"))
        + scale_fill_gradient(low="#000000", high="#ffffff")
        + pnx.new_scale_fill()
        + geom_point(df, aes(fill="g"), shape="o")
        + scale_fill_manual(["red", "blue"])
    )
    fig = draw(p)
    tile, point = built(p).layers
    assert tile.data["fill"].iloc[0] == "#000000"
    assert tile.data["fill"].iloc[-1] == "#ffffff"
    assert set(point.data["fill"]) == {"red", "blue"}
    assert {"z", "g"} <= texts(fig)
    assert legends(p) == {"z": [0], "g": [1]}


def test_default_scales_both_sides(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="h"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    old, new = built(p).layers
    assert old.data["color"].nunique() == 3
    assert new.data["color"].nunique() == 2
    assert legends(p) == {"h": [0], "g": [1]}
    # No renamed columns reach the geom
    assert not any(c.endswith("_new1") for c in old.data.columns)


def test_scales_before_and_after(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="g"))
        + scale_color_manual(["red", "blue"])
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
        + scale_color_manual(["green", "black"], name="other")
    )
    draw(p)
    assert set(built(p).layers[0].data["color"]) == {"red", "blue"}
    assert set(built(p).layers[1].data["color"]) == {"green", "black"}
    assert legends(p) == {"g": [0], "other": [1]}


def test_labels_before_and_after(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="v"))
        + labs(color="Old")
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
        + labs(color="New")
    )
    fig = draw(p)
    assert {"Old", "New"} <= texts(fig)
    assert legends(p) == {"Old": [0], "New": [1]}


def test_stat_default_aesthetic(df):
    # geom_bin_2d maps fill to after_stat("count") by default
    p = (
        ggplot(df, aes("x", "y"))
        + geom_bin_2d(bins=5)
        + pnx.new_scale_fill()
        + geom_point(aes(fill="g"), shape="o")
    )
    draw(p)
    names = [sc.aesthetics for sc in built(p).scales.non_position_scales()]
    assert sorted(names) == [["fill"], ["fill_new1"]]
    assert legends(p) == {"count": [0], "g": [1]}


def test_after_stat_mapping(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_bin_2d(aes(fill=after_stat("density")), bins=5)
        + pnx.new_scale_fill()
        + geom_point(aes(fill="g"), shape="o")
    )
    draw(p)
    assert legends(p) == {"density": [0], "g": [1]}


def test_constant_parameter_is_kept(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(color="red")
        + geom_point(aes(color="h"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    assert set(built(p).layers[0].data["color"]) == {"red"}
    assert legends(p) == {"h": [1], "g": [2]}


def test_three_scales(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="v"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
        + scale_color_manual(["red", "blue"])
        + pnx.new_scale_color()
        + geom_point(aes(color="h"))
    )
    draw(p)
    names = sorted(
        sc.aesthetics[0] for sc in built(p).scales.non_position_scales()
    )
    assert names == ["color", "color_new1", "color_new2"]
    assert set(built(p).layers[1].data["color"]) == {"red", "blue"}
    assert legends(p) == {"v": [0], "g": [1], "h": [2]}


def test_several_aesthetics(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="g", fill="g"), shape="o")
        + pnx.new_scale("colour", "fill")
        + geom_point(aes(color="h", fill="h"), shape="s")
    )
    draw(p)
    # color and fill legends with the same title merge, as usual
    assert legends(p) == {"g": [0], "h": [1]}


def test_global_mapping(df):
    p = (
        ggplot(df, aes("x", "y", color="g"))
        + geom_point()
        + pnx.new_scale_color()
        + geom_line(aes(color="h"))
    )
    draw(p)
    assert built(p).layers[0].data["color"].nunique() == 2
    assert built(p).layers[1].data["color"].nunique() == 3


def test_guides_before(df):
    base = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="h"))
        + guides(color="none")
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    fig = draw(base)
    assert "h" not in texts(fig)
    assert "g" in texts(fig)

    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="h"))
        + guides(color=guide_legend(ncol=3))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    assert built(p).scales.get_scales("color_new1").guide.ncol == 3


def test_show_legend_dict(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="h"), show_legend={"color": False})
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    fig = draw(p)
    assert "h" not in texts(fig)


def test_position_sees_usual_names(df):
    # position_jitterdodge dodges by fill; here it is the renamed fill
    p = (
        ggplot(df, aes("g", "y"))
        + geom_point(aes(fill="h"), shape="o", position=position_jitterdodge())
        + pnx.new_scale_fill()
        + geom_boxplot(aes(fill="g"), alpha=0.3)
    )
    draw(p)
    assert legends(p) == {"h": [0], "g": [1]}


def test_facets(df):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="v"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
        + facet_wrap("h")
    )
    draw(p)
    assert legends(p) == {"v": [0], "g": [1]}


def test_adding_does_not_touch_the_original(df):
    base = ggplot(df, aes("x", "y")) + geom_point(aes(color="g"))
    base += scale_color_manual(["red", "blue"])
    p = base + pnx.new_scale_color()
    assert type(base.layers[0]) is layer
    assert base.scales[0].aesthetics == ["color"]
    assert p.scales[0].aesthetics == ["color_new1"]


def test_redraw_save_and_pickle(df, tmp_path):
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="v"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    draw(p)
    assert legends(p) == {"v": [0], "g": [1]}
    p.save(tmp_path / "f.pdf", verbose=False)
    q = pickle.loads(pickle.dumps(p + geom_point()))
    q.save(tmp_path / "g.png", verbose=False)


def test_plotnine_registry_untouched(df):
    import gc

    from plotnine import geom_point as real
    from plotnine._utils.registry import Registry

    p = (
        ggplot(df, aes("x", "y"))
        + geom_point(aes(color="v"))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    del p
    gc.collect()
    assert Registry["geom_point"] is real


def test_with_rasterise(df):
    p = (
        ggplot(df, aes("x", "y"))
        + pnx.rasterise(geom_point(aes(color="v")))
        + pnx.new_scale_color()
        + geom_point(aes(color="g"))
    )
    draw(p)
    assert legends(p) == {"v": [0], "g": [1]}


@pytest.mark.parametrize("ae", ["x", "y", "label", "group"])
def test_bad_aesthetic(ae):
    with pytest.raises(ValueError, match="Cannot start a new scale"):
        pnx.new_scale(ae)


def test_needs_an_aesthetic():
    with pytest.raises(ValueError):
        pnx.new_scale()
