import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import pytest
from plotnine import aes, facet_wrap, geom_point, ggplot, labs, theme_gray

import plotnine_extensions as pnx
from plotnine_extensions import themes

THEMES = [
    pnx.theme_pubr,
    pnx.theme_pubclean,
    pnx.theme_classic2,
    pnx.theme_cowplot,
    pnx.theme_half_open,
    pnx.theme_minimal_grid,
    pnx.theme_minimal_hgrid,
    pnx.theme_minimal_vgrid,
    pnx.theme_map,
    pnx.theme_nothing,
]


@pytest.fixture
def plot():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "x": rng.normal(size=40),
            "y": rng.normal(size=40),
            "g": np.repeat(["a", "b"], 20),
        }
    )
    return ggplot(df, aes("x", "y", color="g")) + geom_point() + labs(title="t")


def draw(p):
    fig = p.draw()
    return fig, fig.axes[0]


def grid_visible(axis):
    lines = axis.get_gridlines()
    return bool(lines) and lines[0].get_visible()


def is_color(c, ref):
    return np.allclose(mcolors.to_rgba(c), mcolors.to_rgba(ref))


@pytest.mark.parametrize("th", THEMES, ids=lambda t: t.__name__)
def test_renders(plot, th, tmp_path):
    (plot + facet_wrap("g") + th()).save(
        tmp_path / "p.png", width=4, height=3, dpi=50, verbose=False
    )
    assert (tmp_path / "p.png").stat().st_size > 0


def test_every_theme_is_complete(plot):
    # A complete theme replaces the previous one instead of patching it
    for th in THEMES:
        assert th().complete
        assert (theme_gray() + th()).__class__ is th


def test_pubr(plot):
    fig, ax = draw(plot + pnx.theme_pubr())
    assert ax.spines["left"].get_visible()
    assert ax.spines["bottom"].get_visible()
    assert not ax.spines["top"].get_visible()
    assert not grid_visible(ax.xaxis) and not grid_visible(ax.yaxis)
    assert pnx.theme_pubr().themeables.property("legend_position") == "top"


def test_pubr_border_and_angle():
    t = pnx.theme_pubr(border=True, x_text_angle=45, legend="none")
    assert t.themeables.is_blank("axis_line")
    assert t.themeables.property("panel_border", "edgecolor") == "black"
    assert t.themeables.property("axis_text_x", "rotation") == 45
    assert t.themeables.property("axis_text_x", "ha") == "right"
    assert t.themeables.property("legend_position") == "none"


def test_pubclean_grid_direction(plot):
    _, ax = draw(plot + pnx.theme_pubclean())
    assert grid_visible(ax.yaxis) and not grid_visible(ax.xaxis)
    _, ax = draw(plot + pnx.theme_pubclean(flip=True))
    assert grid_visible(ax.xaxis) and not grid_visible(ax.yaxis)


def test_cowplot_sizes():
    t = pnx.theme_cowplot(font_size=10, line_size=2)
    assert t.themeables.property("axis_text_x", "size") == pytest.approx(10 * 12 / 14)
    assert t.themeables.property("plot_title", "size") == pytest.approx(10 * 16 / 14)
    assert t.themeables.property("plot_title", "weight") == "bold"
    assert t.themeables.property("axis_line_x", "linewidth") == 2
    assert t.themeables.is_blank("panel_grid_major_x")


@pytest.mark.parametrize(
    "th, xgrid, ygrid",
    [
        (pnx.theme_minimal_grid, True, True),
        (pnx.theme_minimal_hgrid, False, True),
        (pnx.theme_minimal_vgrid, True, False),
    ],
)
def test_minimal_grids(plot, th, xgrid, ygrid):
    _, ax = draw(plot + th(color="red"))
    assert grid_visible(ax.xaxis) == xgrid
    assert grid_visible(ax.yaxis) == ygrid
    if xgrid:
        assert is_color(ax.xaxis.get_gridlines()[0].get_color(), "red")
    # the axis without a grid keeps a baseline in the grid colour
    if xgrid != ygrid:
        spine = ax.spines["bottom" if ygrid else "left"]
        assert spine.get_visible()
        assert is_color(spine.get_edgecolor(), "red")


def test_map_and_nothing(plot):
    _, ax = draw(plot + pnx.theme_map())
    assert not any(t.get_visible() and t.get_text() for t in ax.get_xticklabels())
    t = pnx.theme_nothing()
    assert t.themeables.property("legend_position") == "none"


def test_grids_on_blank_grid(plot):
    _, ax = draw(plot + pnx.theme_pubr() + pnx.grids("y", color="blue"))
    assert grid_visible(ax.yaxis) and not grid_visible(ax.xaxis)
    assert is_color(ax.yaxis.get_gridlines()[0].get_color(), "blue")
    with pytest.raises(ValueError):
        pnx.grids("z")


def test_background_grid(plot):
    _, ax = draw(
        plot + pnx.theme_minimal_grid() + pnx.background_grid(major="x")
    )
    assert grid_visible(ax.xaxis) and not grid_visible(ax.yaxis)
    _, ax = draw(plot + pnx.theme_cowplot() + pnx.background_grid())
    assert grid_visible(ax.xaxis) and grid_visible(ax.yaxis)
    with pytest.raises(ValueError):
        pnx.background_grid(minor="both")


def test_panel_border_and_bgcolor(plot):
    _, ax = draw(
        plot + pnx.theme_cowplot() + pnx.panel_border(color="green") + pnx.bgcolor("#FFEEDD")
    )
    assert ax.patch.get_visible()
    assert is_color(ax.patch.get_facecolor(), "#FFEEDD")
    t = pnx.theme_pubr(border=True) + pnx.panel_border(remove=True)
    assert t.themeables.is_blank("panel_border")
    t = pnx.theme_classic2() + pnx.border(color="red")
    assert t.themeables.property("panel_border", "edgecolor") == "red"


def test_rremove():
    t = pnx.theme_pubr() + pnx.rremove("x_text", "y.ticks", "legend", "xlab")
    assert t.themeables.is_blank("axis_text_x")
    assert not t.themeables.is_blank("axis_text_y")
    assert t.themeables.is_blank("axis_ticks_major_y")
    assert t.themeables.is_blank("axis_title_x")
    assert t.themeables.property("legend_position") == "none"
    with pytest.raises(ValueError, match="unknown element"):
        pnx.rremove("everything")


def test_rremove_keys_are_real_themeables():
    from plotnine.themes.themeable import themeable

    names = {n for v in themes._REMOVE.values() for n in v}
    names |= {n for v in themes._FONT_TARGETS.values() for n in v}
    assert names <= set(themeable._hierarchy)


def test_font():
    t = pnx.theme_pubr() + pnx.font("title", size=20, color="red", face="bold.italic")
    assert t.themeables.property("plot_title", "size") == 20
    assert t.themeables.property("plot_title", "weight") == "bold"
    assert t.themeables.property("plot_title", "style") == "italic"
    with pytest.raises(ValueError, match="face"):
        pnx.font("title", face="heavy")
    with pytest.raises(ValueError, match="unknown object"):
        pnx.font("axis")


def test_rotate_text():
    t = pnx.rotate_x_text()
    assert t.themeables.property("axis_text_x", "rotation") == 90
    assert t.themeables.property("axis_text_x", "va") == "center"
    t = pnx.rotate_x_text(45)
    assert t.themeables.property("axis_text_x", "va") == "top"
    t = pnx.rotate_y_text()
    assert t.themeables.property("axis_text_y", "rotation") == 90


def test_clean_theme(plot):
    _, ax = draw(plot + pnx.theme_pubr() + pnx.clean_theme())
    assert not ax.spines["left"].get_visible()
