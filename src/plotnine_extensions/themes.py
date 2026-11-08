"""
Publication themes in the spirit of R's ggpubr and cowplot

Line sizes are matplotlib points, as everywhere in plotnine's themes.
plotnine draws ggplot2's default 0.5 mm line as 1 pt, so a ggplot2
``linewidth`` converts to roughly twice its value here.
"""

from __future__ import annotations

from typing import Literal

from plotnine.themes.elements import (
    element_blank,
    element_line,
    element_rect,
    element_text,
    margin,
)
from plotnine.themes.theme import theme
from plotnine.themes.theme_bw import theme_bw
from plotnine.themes.theme_classic import theme_classic
from plotnine.themes.theme_gray import theme_gray
from plotnine.themes.theme_void import theme_void

__all__ = [
    # ggpubr
    "theme_pubr",
    "theme_pubclean",
    "theme_classic2",
    "clean_theme",
    "rotate_x_text",
    "rotate_y_text",
    "rremove",
    "grids",
    "border",
    "bgcolor",
    "font",
    # cowplot
    "theme_cowplot",
    "theme_half_open",
    "theme_minimal_grid",
    "theme_minimal_hgrid",
    "theme_minimal_vgrid",
    "theme_map",
    "theme_nothing",
    "background_grid",
    "panel_border",
]

# ggplot2's 0.5 mm default line is drawn as 1 pt by plotnine's themes
_LW = 2.0

_FACES = {
    "plain": {"weight": "normal", "style": "normal"},
    "bold": {"weight": "bold", "style": "normal"},
    "italic": {"weight": "normal", "style": "italic"},
    "bold.italic": {"weight": "bold", "style": "italic"},
}


def _face(face: str | None) -> dict:
    if face is None:
        return {}
    try:
        return dict(_FACES[face.replace("_", ".")])
    except KeyError:
        raise ValueError(
            f"face must be one of {sorted(_FACES)}, got {face!r}"
        ) from None


# ggpubr ----------------------------------------------------------------


class theme_pubr(theme_bw):
    """
    ggpubr's publication theme: axis lines, no grid, legend on top

    Parameters
    ----------
    base_size : float
        Base font size in points.
    base_family : str, optional
        Font family. If `None`, plotnine's `base_family` option.
    border : bool
        Draw a box around the panel instead of the two axis lines.
    margin : bool
        Keep plotnine's plot margin. `False` shrinks it to almost
        nothing, for panels that will be assembled into a figure.
    legend : str or tuple
        `"top"` (default), `"bottom"`, `"left"`, `"right"`, `"none"`,
        or an `(x, y)` position inside the panel in [0, 1].
    x_text_angle : float
        Rotation of the x tick labels in degrees. Above 5 degrees the
        labels are right-aligned so their ends sit under the ticks.
    """

    def __init__(
        self,
        base_size: float = 12,
        base_family: str | None = None,
        border: bool = False,
        margin: bool = True,
        legend: str | tuple[float, float] = "top",
        x_text_angle: float = 0,
    ):
        super().__init__(base_size, base_family)
        if border:
            frame = {
                "panel_border": element_rect(
                    fill="none", color="black", size=0.7 * _LW
                ),
                "axis_line": element_blank(),
            }
        else:
            frame = {
                "panel_border": element_blank(),
                "axis_line": element_line(color="black", size=0.5 * _LW),
            }
        self += theme(
            panel_grid_major=element_blank(),
            panel_grid_minor=element_blank(),
            axis_text=element_text(color="black"),
            axis_ticks=element_line(color="black"),
            legend_key=element_blank(),
            strip_background=element_rect(
                fill="#F2F2F2", color="black", size=0.7 * _LW
            ),
            strip_text=element_text(color="black"),
            legend_position=legend,
            **frame,
        )
        if not margin:
            self += theme(plot_margin=0.002)
        if x_text_angle:
            self += rotate_x_text(x_text_angle)


class theme_classic2(theme_classic):
    """
    ggpubr's `theme_classic2`: axis lines and no grid, all in black

    Parameters
    ----------
    base_size : float
        Base font size in points.
    base_family : str, optional
        Font family. If `None`, plotnine's `base_family` option.
    """

    def __init__(self, base_size: float = 12, base_family: str | None = None):
        super().__init__(base_size, base_family)
        self += theme(
            axis_line=element_line(color="black", size=0.5 * _LW),
            axis_ticks=element_line(color="black"),
            axis_text=element_text(color="black"),
        )


class theme_pubclean(theme_gray):
    """
    ggpubr's clean theme: white panel, dotted grid along the value axis

    Parameters
    ----------
    base_size : float
        Base font size in points.
    base_family : str, optional
        Font family. If `None`, plotnine's `base_family` option.
    flip : bool
        Grid lines on x instead of y, for horizontal bars and
        `coord_flip`.
    """

    def __init__(
        self,
        base_size: float = 12,
        base_family: str | None = None,
        flip: bool = False,
    ):
        super().__init__(base_size, base_family)
        dotted = element_line(color="#BEBEBE", linetype="dotted", size=0.5 * _LW)
        self += theme(
            panel_background=element_rect(fill="white", color="none"),
            legend_background=element_rect(fill="white", color="none"),
            legend_key=element_rect(fill="white", color="none"),
            legend_position="top",
            panel_grid=element_blank(),
        )
        if flip:
            self += theme(panel_grid_major_x=dotted)
        else:
            self += theme(panel_grid_major_y=dotted)


def clean_theme() -> theme:
    """
    Remove axis lines, ticks, tick labels and axis titles

    For marginal plots and panels that share axes with a neighbour.
    """
    return theme(
        axis_line=element_blank(),
        axis_ticks=element_blank(),
        axis_text=element_blank(),
        axis_title=element_blank(),
    )


def _rotated(angle: float, ha: str | None, va: str | None) -> element_text:
    if ha is None:
        ha = "right" if angle > 5 else "center"
    if va is None:
        va = "center" if abs(angle) == 90 else "top"
    return element_text(rotation=angle, ha=ha, va=va)


def rotate_x_text(
    angle: float = 90,
    ha: Literal["left", "center", "right"] | None = None,
    va: Literal["top", "center", "bottom"] | None = None,
) -> theme:
    """
    Rotate the x tick labels

    Parameters
    ----------
    angle : float
        Degrees counter-clockwise. 90 (default) and 45 are the usual
        choices.
    ha, va : str, optional
        Alignment of each label around its tick. By default a rotated
        label ends under its tick.
    """
    return theme(axis_text_x=_rotated(angle, ha, va))


def rotate_y_text(
    angle: float = 90,
    ha: Literal["left", "center", "right"] | None = None,
    va: Literal["top", "center", "bottom"] | None = None,
) -> theme:
    """
    Rotate the y tick labels

    Parameters
    ----------
    angle : float
        Degrees counter-clockwise; 90 (default) reads bottom to top.
    ha, va : str, optional
        Alignment of each label around its tick.
    """
    if ha is None:
        ha = "center" if abs(angle) == 90 else "right"
    if va is None:
        va = "bottom" if abs(angle) == 90 else "center"
    return theme(
        axis_text_y=element_text(rotation=angle, ha=ha, va=va)
    )


_REMOVE = {
    "grid": ("panel_grid",),
    "x.grid": ("panel_grid_major_x", "panel_grid_minor_x"),
    "y.grid": ("panel_grid_major_y", "panel_grid_minor_y"),
    "axis": ("axis_line",),
    "x.axis": ("axis_line_x",),
    "y.axis": ("axis_line_y",),
    "xlab": ("axis_title_x",),
    "x.title": ("axis_title_x",),
    "ylab": ("axis_title_y",),
    "y.title": ("axis_title_y",),
    "xylab": ("axis_title",),
    "xy.title": ("axis_title",),
    "axis.title": ("axis_title",),
    "legend": (),
    "legend.title": ("legend_title",),
    "ticks": ("axis_ticks",),
    "x.ticks": ("axis_ticks_x",),
    "y.ticks": ("axis_ticks_y",),
    "axis.text": ("axis_text",),
    "xy.text": ("axis_text",),
    "x.text": ("axis_text_x",),
    "y.text": ("axis_text_y",),
}


def rremove(*objects: str) -> theme:
    """
    Remove plot elements by ggpubr's names

    Parameters
    ----------
    *objects : str
        Any of `"grid"`, `"x.grid"`, `"y.grid"`, `"axis"`, `"x.axis"`,
        `"y.axis"`, `"xlab"` (or `"x.title"`), `"ylab"` (`"y.title"`),
        `"xylab"` (`"xy.title"`, `"axis.title"`), `"legend"`,
        `"legend.title"`, `"ticks"`, `"x.ticks"`, `"y.ticks"`,
        `"axis.text"` (`"xy.text"`), `"x.text"`, `"y.text"`.
        Underscores work in place of dots. Several at once:
        `rremove("x.text", "x.ticks")`.
    """
    elements: dict = {}
    for obj in objects:
        key = obj.replace("_", ".")
        if key not in _REMOVE:
            raise ValueError(
                f"rremove: unknown element {obj!r}; "
                f"use one of {sorted(_REMOVE)}"
            )
        if key == "legend":
            elements["legend_position"] = "none"
        for name in _REMOVE[key]:
            elements[name] = element_blank()
    return theme(**elements)


def grids(
    axis: Literal["xy", "x", "y"] = "xy",
    linetype: str = "dashed",
    color: str = "#EBEBEB",
    size: float | None = None,
) -> theme:
    """
    Add major grid lines

    Parameters
    ----------
    axis : {"xy", "x", "y"}
        `"x"` draws the vertical lines (at x breaks), `"y"` the
        horizontal ones.
    linetype, color : str
    size : float, optional
        Line width in points; the theme's grid width if `None`.
    """
    if axis not in ("xy", "x", "y"):
        raise ValueError(f'axis must be "xy", "x" or "y", got {axis!r}')
    line = element_line(linetype=linetype, color=color, size=size)
    return theme(**{f"panel_grid_major_{a}": line for a in axis})


def border(
    color: str = "black", size: float = 0.8 * _LW, linetype: str = "solid"
) -> theme:
    """
    Draw a box around each panel

    Parameters
    ----------
    color, linetype : str
    size : float
        Line width in points.
    """
    return theme(
        panel_border=element_rect(
            fill="none", color=color, size=size, linetype=linetype
        )
    )


def bgcolor(color: str) -> theme:
    """
    Fill the panel background
    """
    return theme(panel_background=element_rect(fill=color, color="none"))


_FONT_TARGETS = {
    "title": ("plot_title",),
    "subtitle": ("plot_subtitle",),
    "caption": ("plot_caption",),
    "xlab": ("axis_title_x",),
    "x.title": ("axis_title_x",),
    "ylab": ("axis_title_y",),
    "y.title": ("axis_title_y",),
    "xylab": ("axis_title",),
    "xy.title": ("axis_title",),
    "axis.title": ("axis_title",),
    "legend.title": ("legend_title",),
    "legend.text": ("legend_text",),
    "x.text": ("axis_text_x",),
    "y.text": ("axis_text_y",),
    "xy.text": ("axis_text",),
    "axis.text": ("axis_text",),
    "strip.text": ("strip_text",),
}


def font(
    object: str,
    size: float | None = None,
    color: str | None = None,
    face: str | None = None,
    family: str | None = None,
) -> theme:
    """
    Change the font of one text element by ggpubr's names

    Parameters
    ----------
    object : str
        `"title"`, `"subtitle"`, `"caption"`, `"xlab"`, `"ylab"`,
        `"xylab"`, `"legend.title"`, `"legend.text"`, `"x.text"`,
        `"y.text"`, `"xy.text"` or `"strip.text"`. Underscores work in
        place of dots.
    size : float, optional
        Points.
    color : str, optional
    face : {"plain", "bold", "italic", "bold.italic"}, optional
    family : str, optional
    """
    key = object.replace("_", ".")
    if key not in _FONT_TARGETS:
        raise ValueError(
            f"font: unknown object {object!r}; "
            f"use one of {sorted(_FONT_TARGETS)}"
        )
    props = {"size": size, "color": color, "family": family, **_face(face)}
    props = {k: v for k, v in props.items() if v is not None}
    return theme(
        **{name: element_text(**props) for name in _FONT_TARGETS[key]}
    )


# cowplot ---------------------------------------------------------------


class theme_cowplot(theme_gray):
    """
    cowplot's default theme: open axes, no grid, black text

    Also available as `theme_half_open`, its name since cowplot 1.0.

    Parameters
    ----------
    font_size : float
        Base font size in points. Tick labels, legend text and strip
        text are `rel_small` times this, the title `rel_large`, the
        caption `rel_tiny`.
    font_family : str, optional
        Font family. If `None`, plotnine's `base_family` option.
    line_size : float
        Width of axis lines and ticks, in points. 1 pt is what plotnine
        draws for cowplot's default `line_size = 0.5` (mm).
    rel_small, rel_tiny, rel_large : float
        Text sizes relative to `font_size`.
    """

    def __init__(
        self,
        font_size: float = 14,
        font_family: str | None = None,
        line_size: float = 1.0,
        rel_small: float = 12 / 14,
        rel_tiny: float = 11 / 14,
        rel_large: float = 16 / 14,
    ):
        super().__init__(font_size, font_family)
        half_line = font_size / 2
        small = rel_small * font_size
        self += theme(
            line=element_line(color="black", size=line_size),
            text=element_text(color="black"),
            axis_line=element_line(
                color="black", size=line_size, lineend="projecting"
            ),
            axis_text=element_text(color="black", size=small),
            axis_text_x=element_text(margin=margin(t=small / 4)),
            axis_text_y=element_text(margin=margin(r=small / 4)),
            axis_ticks=element_line(color="black", size=line_size),
            axis_ticks_length_major=half_line / 2,
            legend_background=element_blank(),
            legend_key=element_blank(),
            legend_key_size=1.1 * font_size,
            legend_text=element_text(size=small),
            legend_title=element_text(ha="left"),
            panel_background=element_blank(),
            panel_border=element_blank(),
            panel_grid=element_blank(),
            strip_background=element_rect(fill="#CCCCCC", color="none"),
            strip_text=element_text(color="black", size=small),
            plot_title=element_text(
                size=rel_large * font_size, weight="bold", ha="left"
            ),
            plot_subtitle=element_text(size=small, ha="left"),
            plot_caption=element_text(size=rel_tiny * font_size),
            plot_tag=element_text(weight="bold"),
        )


class theme_half_open(theme_cowplot):
    """
    cowplot's `theme_half_open`, identical to `theme_cowplot`

    Parameters are those of `theme_cowplot`.
    """


class _minimal(theme_cowplot):
    _grid: str = "xy"

    def __init__(
        self,
        font_size: float = 14,
        font_family: str | None = None,
        line_size: float = 1.0,
        rel_small: float = 12 / 14,
        rel_tiny: float = 11 / 14,
        rel_large: float = 16 / 14,
        color: str = "#D9D9D9",
    ):
        super().__init__(
            font_size, font_family, line_size, rel_small, rel_tiny, rel_large
        )
        grid = element_line(color=color, size=line_size)
        if self._grid == "xy":
            self += theme(
                axis_line=element_blank(),
                axis_ticks=element_blank(),
                panel_grid_major=grid,
            )
            return
        # One grid direction; the other axis keeps a line and ticks in
        # the grid colour, so the bars or points have a baseline.
        other = "x" if self._grid == "y" else "y"
        self += theme(**{f"panel_grid_major_{self._grid}": grid})
        self += theme(
            **{
                f"axis_line_{self._grid}": element_blank(),
                f"axis_ticks_{self._grid}": element_blank(),
                f"axis_line_{other}": element_line(
                    color=color, size=line_size
                ),
                f"axis_ticks_{other}": element_line(
                    color=color, size=line_size
                ),
            }
        )


_MINIMAL_DOC = """
    cowplot's minimal theme with {what}

    Parameters
    ----------
    font_size, font_family, line_size, rel_small, rel_tiny, rel_large
        As in `theme_cowplot`.
    color : str
        Colour of the grid lines{extra}. Default `"#D9D9D9"` is R's
        `"grey85"`.
"""


class theme_minimal_grid(_minimal):
    __doc__ = _MINIMAL_DOC.format(
        what="major grid lines and no axis lines or ticks", extra=""
    )
    _grid = "xy"


class theme_minimal_hgrid(_minimal):
    __doc__ = _MINIMAL_DOC.format(
        what="horizontal grid lines only, for vertical bars",
        extra=", the x axis line and the x ticks",
    )
    _grid = "y"


class theme_minimal_vgrid(_minimal):
    __doc__ = _MINIMAL_DOC.format(
        what="vertical grid lines only, for horizontal bars",
        extra=", the y axis line and the y ticks",
    )
    _grid = "x"


class theme_map(theme_cowplot):
    """
    cowplot's map theme: no axes, ticks, tick labels or axis titles

    For maps, images and embeddings (UMAP, t-SNE) where the axis values
    mean nothing. Parameters are those of `theme_cowplot`.
    """

    def __init__(
        self,
        font_size: float = 14,
        font_family: str | None = None,
        line_size: float = 1.0,
        rel_small: float = 12 / 14,
        rel_tiny: float = 11 / 14,
        rel_large: float = 16 / 14,
    ):
        super().__init__(
            font_size, font_family, line_size, rel_small, rel_tiny, rel_large
        )
        self += clean_theme()


class theme_nothing(theme_void):
    """
    cowplot's `theme_nothing`: no axes, no legend, no margin

    For images and plot elements that go into a composed figure.

    Parameters
    ----------
    font_size : float
        Base font size in points.
    font_family : str, optional
        Font family. If `None`, plotnine's `base_family` option.
    """

    def __init__(self, font_size: float = 14, font_family: str | None = None):
        super().__init__(font_size, font_family)
        self += theme(legend_position="none", plot_margin=0)


def background_grid(
    major: Literal["xy", "x", "y", "none"] = "xy",
    minor: Literal["xy", "x", "y", "none"] = "none",
    size_major: float = 0.5 * _LW,
    size_minor: float = 0.2 * _LW,
    color_major: str = "#D9D9D9",
    color_minor: str = "#D9D9D9",
) -> theme:
    """
    Set grid lines on any theme, as cowplot's `background_grid`

    Parameters
    ----------
    major, minor : {"xy", "x", "y", "none"}
        Which grid lines to draw. `"x"` is the vertical lines (at x
        breaks), `"y"` the horizontal ones. Directions not named are
        removed.
    size_major, size_minor : float
        Line widths in points.
    color_major, color_minor : str
        Default `"#D9D9D9"` is R's `"grey85"`.
    """
    elements: dict = {}
    for kind, which, size, color in (
        ("major", major, size_major, color_major),
        ("minor", minor, size_minor, color_minor),
    ):
        if which not in ("xy", "x", "y", "none"):
            raise ValueError(
                f'{kind} must be "xy", "x", "y" or "none", got {which!r}'
            )
        for a in "xy":
            elements[f"panel_grid_{kind}_{a}"] = (
                element_line(color=color, size=size)
                if a in which
                else element_blank()
            )
    return theme(**elements)


def panel_border(
    color: str = "#D9D9D9",
    size: float = 1 * _LW,
    linetype: str = "solid",
    remove: bool = False,
) -> theme:
    """
    Draw or remove a box around each panel, as cowplot's `panel_border`

    Parameters
    ----------
    color : str
        Default `"#D9D9D9"` is R's `"grey85"`.
    size : float
        Line width in points.
    linetype : str
    remove : bool
        Remove the border instead.
    """
    if remove:
        return theme(panel_border=element_blank())
    return theme(
        panel_border=element_rect(
            fill="none", color=color, size=size, linetype=linetype
        )
    )
