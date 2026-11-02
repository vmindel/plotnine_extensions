from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from matplotlib.text import Text
from plotnine._utils import (
    SIZE_FACTOR,
    order_as_data_mapping,
    remove_missing,
    to_rgba,
)
from plotnine.geoms.geom import geom
from plotnine.geoms.geom_label import geom_label
from plotnine.geoms.geom_text import geom_text

from ._artist import RepelLabels, RepelSettings

if TYPE_CHECKING:
    from typing import Any

    from matplotlib.axes import Axes
    from plotnine import aes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view
    from plotnine.typing import DataLike

_REPEL_PARAMS: dict[str, Any] = {
    "box_padding": 3.0,
    "point_padding": 0.0,
    "point_size": 1.5,
    "min_segment_length": 6.0,
    "segment_color": None,
    "segment_size": 0.5,
    "segment_alpha": None,
    "segment_linetype": "solid",
    "arrow": None,
    "force": 1.0,
    "force_pull": 1.0,
    "max_iter": 10_000,
    "max_time": 1.0,
    "max_overlaps": 10,
    "direction": "both",
    "seed": 1,
    "xlim": None,
    "ylim": None,
}

_PARAMS_DOC = """
    box_padding : float, default=3
        Space (points) kept free around each label.
    point_padding : float, default=0
        Extra space (points) kept free around each data point.
    point_size : float, default=1.5
        Size of the data points, in the units of `geom_point`'s `size`,
        so labels avoid the markers and not just their centres. Set it to
        the size of the points you draw.
    min_segment_length : float, default=6
        Segments shorter than this (points) are not drawn.
    segment_color : str, default=None
        Segment colour. `None` uses the label's colour.
    segment_size : float, default=0.5
        Segment line width, in points.
    segment_alpha : float, default=None
        Segment transparency. `None` uses the label's alpha.
    segment_linetype : str, default="solid"
        Segment line style.
    arrow : dict, default=None
        If given, segments end in an arrow at the data point. The dict
        goes to matplotlib's `FancyArrowPatch`, e.g.
        `{"arrowstyle": "-|>", "mutation_scale": 8}`.
    force : float, default=1
        Strength of repulsion between overlapping labels and points.
    force_pull : float, default=1
        Strength of the pull of each label towards its point.
    max_iter : int, default=10000
        Maximum iterations of the placement.
    max_time : float, default=1
        Maximum seconds spent placing labels, per panel and draw.
    max_overlaps : float, default=10
        A label that, after placement, still overlaps more than this many
        other labels and points is not drawn. Earlier rows win, so sort
        the data by priority. Use `np.inf` to keep every label.
    direction : str, default="both"
        Move labels in `"both"`, only `"x"` or only `"y"` directions.
    seed : int, default=1
        Seed of the random tie-breaking, so a figure renders the same
        every time. `None` for a different layout each draw.
    xlim, ylim : tuple, default=None
        Data range, `(min, max)`, that labels must stay within, in the
        units of the data (before any scale transformation such as log).
        Either end can be `None` for the panel edge.
    nudge_x, nudge_y : float, default=0
        Data-unit offset of each label's starting position. Unlike in
        `geom_text`, segments still point at the original position.
"""


def _is_label(values: pd.Series) -> np.ndarray:
    def ok(v):
        if v is None:
            return False
        if isinstance(v, float) and np.isnan(v):
            return False
        return str(v) != ""

    return np.array([ok(v) for v in values], dtype=bool)


def _texts(data: pd.DataFrame, params: dict[str, Any], boxed: bool):
    color = to_rgba(data["color"], data["alpha"])
    if isinstance(color, tuple):
        color = [color] * len(data)

    texts = []
    pads = []
    for k, (_, row) in enumerate(data.iterrows()):
        t = Text(
            text=str(row["label"]),
            color=color[k],
            fontsize=row["size"],
            rotation=row["angle"],
            linespacing=row["lineheight"],
            fontfamily=row["family"],
            fontweight=row["fontweight"],
            fontstyle=row["fontstyle"],
            fontvariant=row["fontvariant"] or "normal",
            multialignment=row["ha"],
            zorder=params["zorder"],
            rasterized=params["raster"],
        )
        if params["path_effects"]:
            t.set_path_effects(params["path_effects"])
        if boxed:
            tokens = [params["boxstyle"], f"pad={params['label_padding']}"]
            if params["boxstyle"] in {"round", "round4"}:
                tokens.append(f"rounding_size={params['label_r']}")
            elif params["boxstyle"] in {"roundtooth", "sawtooth"}:
                tokens.append(f"tooth_size={params['tooth_size']}")
            t.set_bbox(
                {
                    "boxstyle": ",".join(tokens),
                    "facecolor": to_rgba(row["fill"], row["alpha"]),
                    "edgecolor": params["boxcolor"] or color[k],
                    "linewidth": params["label_size"],
                }
            )
            pads.append(params["label_padding"] * row["size"])
        texts.append(t)
    return texts, np.asarray(pads, float)


def _scale_limits(lim, view):
    """
    Map user-unit limits through the panel's scale transformation
    """
    if lim is None:
        return None
    transform = getattr(getattr(view, "scale", None), "transform", None)
    out = []
    for v in lim:
        if v is None or transform is None:
            out.append(v)
            continue
        try:
            out.append(float(np.asarray(transform([v]), dtype=float)[0]))
        except (TypeError, ValueError):
            out.append(v)
    if transform is not None:
        # A decreasing transformation (e.g. reverse) swaps the ends
        try:
            probe = np.asarray(transform([1.0, 2.0]), dtype=float)
            if probe[1] < probe[0]:
                out = out[::-1]
        except (TypeError, ValueError):
            pass
    return tuple(out)


def _draw_repel(
    data: pd.DataFrame,
    coord: coord,
    panel_params: panel_view,
    ax: Axes,
    params: dict[str, Any],
    boxed: bool,
):
    data = coord.transform(data, panel_params)
    data = data.reset_index(drop=True)
    labelled = _is_label(data["label"])
    if not labelled.any():
        return

    label_data = data[labelled]
    label_index = np.flatnonzero(labelled)
    points = data[["x", "y"]].to_numpy(float)
    nudge = np.column_stack(
        [
            np.broadcast_to(params["nudge_x"], len(data))[labelled],
            np.broadcast_to(params["nudge_y"], len(data))[labelled],
        ]
    )
    nudged = points[label_index] + nudge

    texts, pads = _texts(label_data, params, boxed)

    seg_color = params["segment_color"]
    seg_alpha = params["segment_alpha"]
    if seg_color is not None or seg_alpha is not None:
        base = seg_color if seg_color is not None else label_data["color"].iloc[0]
        alpha = seg_alpha if seg_alpha is not None else label_data["alpha"].iloc[0]
        seg_color = to_rgba(base, alpha)

    settings = RepelSettings(
        box_padding=params["box_padding"],
        point_padding=params["point_padding"],
        # Same marker diameter, in points, as geom_point
        point_radius=params["point_size"] * SIZE_FACTOR / 2,
        min_segment_length=params["min_segment_length"],
        segment_color=seg_color,
        segment_linewidth=params["segment_size"],
        segment_linestyle=params["segment_linetype"],
        arrow=params["arrow"],
        force=params["force"],
        force_pull=params["force_pull"],
        max_iter=params["max_iter"],
        max_time=params["max_time"],
        max_overlaps=params["max_overlaps"],
        direction=params["direction"],
        seed=params["seed"],
        xlim=_scale_limits(params["xlim"], panel_params.x),
        ylim=_scale_limits(params["ylim"], panel_params.y),
        label_pad=pads,
    )
    artist = RepelLabels(ax, points, label_index, nudged, texts, settings)
    artist.set_zorder(params["zorder"])
    ax.add_artist(artist)


class geom_text_repel(geom_text):
    __doc__ = f"""
    Text labels that repel each other and the data points

    Labels are placed when the figure is rendered, using the final panel
    size and output resolution, and connected to their points by a
    segment when they had to move.

    Rows with an empty or missing label are not labelled, but their
    points still push labels away. Use that to keep labels off points
    you do not want to label.

    Parameters
    ----------
    mapping : aes, default=None
        Aesthetic mappings. `x`, `y` and `label` are required; `color`,
        `size`, `alpha`, `angle`, `family`, `fontweight`, `fontstyle`
        and `lineheight` work as in `geom_text`.
    data : DataFrame, default=None
        Layer data, if different from the plot's.
    {_PARAMS_DOC.strip()}
    parse, format_string, path_effects :
        As in `geom_text`.
    """

    # Spelled out in full: plotnine 0.15 does not merge DEFAULT_PARAMS
    # along the class hierarchy, later versions do.
    DEFAULT_PARAMS = {**geom_text.DEFAULT_PARAMS, **_REPEL_PARAMS}

    def __init__(
        self,
        mapping: aes | None = None,
        data: DataLike | None = None,
        **kwargs: Any,
    ):
        data, mapping = order_as_data_mapping(data, mapping)
        if kwargs.get("adjust_text") is not None:
            raise ValueError(
                f"{type(self).__name__} places labels itself; "
                "do not pass adjust_text"
            )
        if mapping and "hjust" in mapping:
            mapping["ha"] = mapping.pop("hjust")
        if mapping and "vjust" in mapping:
            mapping["va"] = mapping.pop("vjust")
        # Skip geom_text.__init__: it turns nudges into position_nudge,
        # which would move the points as well as the labels.
        geom.__init__(self, mapping, data, **kwargs)

        if self.params["direction"] not in ("both", "x", "y"):
            raise ValueError(
                "direction must be one of 'both', 'x', 'y', "
                f"got {self.params['direction']!r}"
            )

    def handle_na(self, data: pd.DataFrame) -> pd.DataFrame:
        # A missing label means "unlabelled point", not a row to drop
        return remove_missing(
            data,
            self.params["na_rm"],
            ["x", "y"],
            type(self).__name__,
        )

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        _draw_repel(data, coord, panel_params, ax, self.params, boxed=False)


class geom_label_repel(geom_text_repel):
    __doc__ = f"""
    Boxed text labels that repel each other and the data points

    See `geom_text_repel` for how placement works.

    Parameters
    ----------
    mapping : aes, default=None
        Aesthetic mappings. `x`, `y` and `label` are required; `color`,
        `size`, `alpha`, `angle`, `family`, `fontweight`, `fontstyle`
        and `lineheight` work as in `geom_text`.
    data : DataFrame, default=None
        Layer data, if different from the plot's.
    {_PARAMS_DOC.strip()}
    parse, format_string, path_effects :
        As in `geom_text`.
    boxstyle, boxcolor, label_padding, label_r, label_size, tooth_size :
        Label box styling, as in `geom_label`. `fill` is an aesthetic.
    """

    DEFAULT_AES = {**geom_text.DEFAULT_AES, "fill": "white"}
    DEFAULT_PARAMS = {
        **geom_text_repel.DEFAULT_PARAMS,
        **geom_label.DEFAULT_PARAMS,
        **_REPEL_PARAMS,
    }
    draw_legend = staticmethod(geom_label.draw_legend)

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        _draw_repel(data, coord, panel_params, ax, self.params, boxed=True)
