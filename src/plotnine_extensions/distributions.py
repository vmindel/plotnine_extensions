"""
Distributions with their summaries: point intervals, half-eyes, rainclouds

In the spirit of R's ggdist. Draw vertically (categories on x); add
``coord_flip()`` for horizontal plots.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from plotnine import geom_boxplot, geom_point, geom_violin, position_nudge
from plotnine._utils import SIZE_FACTOR, to_rgba
from plotnine.geoms.geom import geom
from plotnine.positions.position_jitter import position_jitter
from plotnine.stats.stat import stat

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from matplotlib.axes import Axes
    from plotnine import aes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view

__all__ = [
    "geom_pointinterval",
    "geom_raincloud",
    "position_jitternudge",
    "stat_halfeye",
    "stat_pointinterval",
]

_POINT_FUNS = {"median": np.median, "mean": np.mean}


class stat_pointinterval(stat):
    """
    Point summary and quantile intervals per group

    Parameters
    ----------
    point : {"median", "mean"}, default="median"
        The point summary.
    widths : sequence of float, default=(0.66, 0.95)
        Probability mass of each interval; each is the equal-tailed
        quantile interval, e.g. 0.95 spans the 2.5% and 97.5% quantiles.

    Notes
    -----
    Computed variables: ``y`` (the point), ``ymin``/``ymax`` (interval),
    ``interval_width`` (its probability mass), ``n`` (group size).
    """

    REQUIRED_AES = {"x", "y"}
    DEFAULT_PARAMS = {
        "geom": "pointinterval",
        "position": "identity",
        "na_rm": False,
        "point": "median",
        "widths": (0.66, 0.95),
    }
    CREATES = {"ymin", "ymax", "interval_width", "n"}

    def __init__(self, mapping=None, data=None, **kwargs):
        point = kwargs.get("point", "median")
        if point not in _POINT_FUNS:
            raise ValueError(f"point must be one of {list(_POINT_FUNS)}, got {point!r}")
        widths = kwargs.get("widths", (0.66, 0.95))
        if not all(0 < w < 1 for w in widths):
            raise ValueError(f"widths must be between 0 and 1, got {widths}")
        super().__init__(mapping, data, **kwargs)

    def compute_group(self, data: pd.DataFrame, scales) -> pd.DataFrame:
        y = data["y"].to_numpy(float)
        point = _POINT_FUNS[self.params["point"]](y)
        rows = []
        for w in sorted(self.params["widths"], reverse=True):
            lo, hi = np.quantile(y, [(1 - w) / 2, 1 - (1 - w) / 2])
            rows.append(
                {
                    "x": data["x"].iloc[0],
                    "y": point,
                    "ymin": lo,
                    "ymax": hi,
                    "interval_width": w,
                    "n": len(y),
                }
            )
        return pd.DataFrame(rows)


class geom_pointinterval(geom):
    """
    Point with one or more intervals

    Wider intervals are drawn thinner. Use with `stat_pointinterval`, or
    with precomputed `y`, `ymin`, `ymax` and `interval_width`.

    Parameters
    ----------
    interval_size : (float, float), default=(0.6, 1.8)
        Line width (geom size units) of the widest and the narrowest
        interval.
    point_size : float, default=1.8
        Size of the point.
    """

    DEFAULT_AES = {
        "alpha": 1,
        "color": "black",
        "fill": "black",
        "linetype": "solid",
        "interval_width": None,
    }
    REQUIRED_AES = {"x", "y", "ymin", "ymax"}
    DEFAULT_PARAMS = {
        "stat": "pointinterval",
        "position": "identity",
        "na_rm": False,
        "interval_size": (0.6, 1.8),
        "point_size": 1.8,
    }

    @staticmethod
    def draw_legend(data: pd.Series, da, lyr):
        """
        The narrowest interval with the point on it, as in the panel

        The sizes come from the `interval_size` and `point_size`
        parameters; the geom has no size aesthetic.
        """
        from matplotlib.lines import Line2D

        params = lyr.geom.params
        color = to_rgba(data["color"], data["alpha"])
        fill = data["fill"] if data["fill"] is not None else data["color"]
        y = 0.5 * da.height
        da.add_artist(
            Line2D(
                [0, da.width],
                [y, y],
                linewidth=params["interval_size"][1] * SIZE_FACTOR,
                color=color,
                solid_capstyle="butt",
            )
        )
        # The panel's scatter takes the area; a marker takes the diameter
        da.add_artist(
            Line2D(
                [0.5 * da.width],
                [y],
                marker="o",
                markersize=params["point_size"] * SIZE_FACTOR + 0.5,
                markerfacecolor=to_rgba(fill, data["alpha"]),
                markeredgecolor=color,
                markeredgewidth=0.5,
            )
        )
        return da

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        from matplotlib.collections import LineCollection

        if not len(data):
            return
        data = coord.transform(data, panel_params)
        # coord_flip renames the columns; draw along whichever axis holds
        # the interval
        if "ymin" in data:
            pos, lo, hi, val = "x", "ymin", "ymax", "y"
        else:
            pos, lo, hi, val = "y", "xmin", "xmax", "x"

        widths = data["interval_width"]
        if widths.isna().all():
            widths = pd.Series(np.ones(len(data)), index=data.index)
        thin, thick = self.params["interval_size"]
        unique = np.sort(widths.unique())
        rank = {w: i for i, w in enumerate(unique)}
        frac = np.array(
            [1 - rank[w] / max(1, len(unique) - 1) for w in widths]
        )
        lw = (thin + (thick - thin) * frac) * SIZE_FACTOR

        def xy(p, v):
            return (p, v) if pos == "x" else (v, p)

        segments = [
            [xy(p, a), xy(p, b)] for p, a, b in zip(data[pos], data[lo], data[hi])
        ]
        color = to_rgba(data["color"], data["alpha"])
        order = np.argsort(-frac)  # thin, wide intervals drawn first
        ax.add_collection(
            LineCollection(
                [segments[i] for i in order[::-1]],
                colors=[color[i] for i in order[::-1]]
                if not isinstance(color, tuple)
                else color,
                linewidths=lw[order[::-1]],
                linestyles="solid",
                capstyle="butt",
                zorder=self.params["zorder"],
                rasterized=self.params["raster"],
            )
        )
        points = data.drop_duplicates(subset=[pos, val, "group"])
        px, py = xy(points[pos], points[val])
        size = self.params["point_size"]
        ax.scatter(
            px,
            py,
            s=(size * SIZE_FACTOR + 0.5) ** 2,
            c=to_rgba(points["fill"], points["alpha"]),
            edgecolors=to_rgba(points["color"], points["alpha"]),
            linewidths=0.5,
            zorder=self.params["zorder"] + 0.1,
            rasterized=self.params["raster"],
        )


class position_jitternudge(position_jitter):
    """
    Jitter, then shift

    Puts raw points beside a summary instead of on top of it.

    Parameters
    ----------
    width, height : float
        Jitter amount: points move up to this far either way.
    nudge_x, nudge_y : float
        Shift applied after jittering.
    random_state : int, optional
        Seed for reproducible jitter.
    """

    def __init__(
        self,
        width: float | None = 0.08,
        height: float | None = 0,
        nudge_x: float = -0.2,
        nudge_y: float = 0,
        random_state=None,
    ):
        super().__init__(width=width, height=height, random_state=random_state)
        self.params["nudge_x"] = nudge_x
        self.params["nudge_y"] = nudge_y

    def setup_params(self, data):
        params = super().setup_params(data)
        params["nudge_x"] = self.params["nudge_x"]
        params["nudge_y"] = self.params["nudge_y"]
        return params

    @classmethod
    def compute_layer(cls, data, params, layout):
        data = super().compute_layer(data, params, layout)
        data = deepcopy(data)
        if params["nudge_x"]:
            for col in ("x", "xmin", "xmax", "xend"):
                if col in data:
                    data[col] = data[col] + params["nudge_x"]
        if params["nudge_y"]:
            for col in ("y", "ymin", "ymax", "yend"):
                if col in data:
                    data[col] = data[col] + params["nudge_y"]
        return data


def stat_halfeye(
    mapping: aes | None = None,
    data: pd.DataFrame | None = None,
    *,
    width: float = 0.9,
    fill: str = "#8fa9c7",
    adjust: float = 1,
    scale: str = "area",
    point: str = "median",
    widths: Sequence[float] = (0.66, 0.95),
    nudge: float = 0,
    **slab_kwargs: Any,
) -> list:
    """
    Half-eye: a density slab with a point and intervals at its base

    Parameters
    ----------
    mapping, data
        As for any layer; `x` is the category, `y` the values.
    width : float, default=0.9
        Maximum slab thickness, as a fraction of the distance between
        categories.
    fill : str
        Slab colour, unless `fill` is mapped.
    adjust : float, default=1
        Bandwidth multiplier of the density.
    scale : {"area", "count", "width"}, default="area"
        Slab scaling across categories, as in `geom_violin`: equal areas
        (densities on one scale), areas proportional to group size, or
        equal maximum thickness.
    point, widths
        As in `stat_pointinterval`.
    nudge : float, default=0
        Shift of the whole half-eye along x.
    **slab_kwargs
        Passed to the slab (`geom_violin`), e.g. ``alpha``.

    Returns
    -------
    list
        Two layers; add them with ``+``.
    """
    slab_params: dict[str, Any] = {"color": None, **slab_kwargs}
    if mapping is None or "fill" not in dict(mapping):
        slab_params.setdefault("fill", fill)
    # Not dodged: slabs are wider than the gap between categories
    position = position_nudge(x=nudge) if nudge else "identity"
    return [
        geom_violin(
            _without(mapping, "color"),
            data,
            style="right",
            width=2 * width,
            adjust=adjust,
            scale=scale,
            trim=True,
            position=position,
            **slab_params,
        ),
        stat_pointinterval(
            mapping,
            data,
            point=point,
            widths=widths,
            position=position_nudge(x=nudge) if nudge else "identity",
        ),
    ]


def geom_raincloud(
    mapping: aes | None = None,
    data: pd.DataFrame | None = None,
    *,
    width: float = 0.6,
    fill: str = "#8fa9c7",
    adjust: float = 1,
    box_width: float = 0.1,
    jitter: float = 0.06,
    point_size: float = 0.8,
    point_alpha: float = 0.5,
    seed: int | None = 1,
) -> list:
    """
    Raincloud: half density, box plot and the raw points

    A density slab to the right of each category, a narrow box plot
    on the category, and the jittered observations to its left, after
    Allen et al. (2019, Wellcome Open Research) "Raincloud plots: a
    multi-platform tool for robust data visualization".

    Parameters
    ----------
    mapping, data
        As for any layer; `x` is the category, `y` the values.
    width : float, default=0.6
        Maximum slab thickness.
    fill : str
        Slab and box colour, unless `fill` is mapped.
    adjust : float, default=1
        Bandwidth multiplier of the density.
    box_width : float, default=0.1
        Width of the box plot; 0 leaves it out.
    jitter : float, default=0.06
        Horizontal jitter of the points (either way).
    point_size, point_alpha : float
        Appearance of the points.
    seed : int, optional
        Seed of the jitter, so the figure is reproducible.

    Returns
    -------
    list
        Layers; add them with ``+``.
    """
    mapped_fill = mapping is not None and "fill" in dict(mapping)
    fill_param = {} if mapped_fill else {"fill": fill}
    gap = box_width / 2 + 0.03
    layers: list = [
        geom_violin(
            _without(mapping, "color"),
            data,
            style="right",
            width=2 * width,
            adjust=adjust,
            trim=True,
            color=None,
            position=position_nudge(x=gap),
            **fill_param,
        )
    ]
    if box_width:
        layers.append(
            geom_boxplot(
                mapping,
                data,
                width=box_width,
                outlier_shape="",
                alpha=0.8,
                **fill_param,
            )
        )
    layers.append(
        geom_point(
            mapping,
            data,
            size=point_size,
            alpha=point_alpha,
            position=position_jitternudge(
                width=jitter,
                height=0,
                nudge_x=-(gap + jitter + 0.03),
                random_state=seed,
            ),
        )
    )
    return layers


def _without(mapping: aes | None, ae: str) -> aes | None:
    """
    The mapping minus one aesthetic

    The slabs take no outline colour (``color=None``); a mapped colour
    is for the intervals, points and boxes, as in ggdist.
    """
    if mapping is None:
        return None
    from plotnine import aes as make_aes

    return make_aes(**{k: v for k, v in mapping.items() if k != ae})
