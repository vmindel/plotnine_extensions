"""
Curved segments, as in ggplot2's geom_curve
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.patches import ConnectionStyle
from matplotlib.path import Path
from plotnine._utils import SIZE_FACTOR, to_rgba
from plotnine.geoms.geom_segment import geom_segment

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.axes import Axes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view

__all__ = ["geom_curve"]


class _Bend(ConnectionStyle._Base):  # pyright: ignore[reportAttributeAccessIssue]
    """
    Quadratic Bezier between two points, computed in display space

    The control point sits at ``angle`` / 180 of the way from start to end
    and ``curvature`` times the start-end distance off the line, to the
    right of the direction of travel for positive curvature.
    """

    def __init__(self, curvature: float, angle: float):
        self.curvature = curvature
        self.angle = angle

    def connect(self, posA, posB):
        (x0, y0), (x1, y1) = posA, posB
        dx, dy = x1 - x0, y1 - y0
        t = self.angle / 180
        cx = x0 + t * dx + self.curvature * dy
        cy = y0 + t * dy - self.curvature * dx
        return Path(
            [(x0, y0), (cx, cy), (x1, y1)],
            [Path.MOVETO, Path.CURVE3, Path.CURVE3],
        )


def _arrowstyle(arrow) -> tuple[str, dict]:
    """
    matplotlib arrow style for a plotnine `arrow`
    """
    if arrow is None:
        return "-", {}
    head = {"open": ">", "closed": "|>"}[arrow.type]
    tail = {"open": "<", "closed": "<|"}[arrow.type]
    style = {"last": f"-{head}", "first": f"{tail}-", "both": f"{tail}-{head}"}[
        arrow.ends
    ]
    # plotnine arrow sizes are inches; matplotlib's are points
    length = arrow.length * 72
    half_width = length * np.tan(np.radians(arrow.angle))
    return style, {"head_length": length, "head_width": half_width}


class geom_curve(geom_segment):
    """
    Curved line segments

    Like `geom_segment`, from (`x`, `y`) to (`xend`, `yend`), but curved.
    The curve is computed on screen, so it keeps its shape whatever the
    scales of the axes.

    Parameters
    ----------
    curvature : float, default=0.5
        How far the curve bows away from the straight line, as a fraction
        of the segment's length. Positive values bow to the right of the
        direction of travel, negative to the left, 0 is straight.
    angle : float, default=90
        Where along the segment the curve peaks, in degrees from 0 to 180:
        90 is symmetric, smaller values skew the bend towards the start,
        larger towards the end.
    arrow : plotnine.arrow, default=None
        Arrow heads, as for `geom_segment`.
    lineend : str, default="butt"
        Line end style.
    shrink : float or (float, float), default=0
        Stop the curve this many points short of its start and end, e.g.
        so arrow heads are not hidden under point markers. Not in ggplot2.

    Notes
    -----
    The curve is a single quadratic Bezier. ggplot2's `geom_curve` uses a
    smoother spline through several control points (`ncp`), so curves look
    similar but not identical; the sign convention of `curvature` has not
    been checked against ggplot2.
    """

    DEFAULT_PARAMS = {
        **geom_segment.DEFAULT_PARAMS,
        "curvature": 0.5,
        "angle": 90,
        "shrink": 0,
    }

    def __init__(self, mapping=None, data=None, **kwargs):
        angle = kwargs.get("angle", 90)
        if not 0 < angle < 180:
            raise ValueError(f"angle must be between 0 and 180, got {angle}")
        super().__init__(mapping, data, **kwargs)

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        from matplotlib.patches import FancyArrowPatch

        data = coord.transform(data, panel_params)
        params = self.params
        connection = _Bend(params["curvature"], params["angle"])
        style, head = _arrowstyle(params["arrow"])
        shrink = params["shrink"]
        shrink_a, shrink_b = (shrink, shrink) if np.isscalar(shrink) else shrink
        if head:
            style = style + "," + ",".join(f"{k}={v}" for k, v in head.items())
        color = to_rgba(data["color"], data["alpha"])
        if isinstance(color, tuple):
            color = [color] * len(data)

        for i, (x0, y0, x1, y1, lw, ls) in enumerate(
            zip(
                data["x"],
                data["y"],
                data["xend"],
                data["yend"],
                data["size"] * SIZE_FACTOR,
                data["linetype"],
            )
        ):
            patch = FancyArrowPatch(
                (x0, y0),
                (x1, y1),
                connectionstyle=connection,
                arrowstyle=style,
                shrinkA=shrink_a,
                shrinkB=shrink_b,
                mutation_scale=1,
                color=color[i],
                linewidth=lw,
                linestyle=ls,
                capstyle=params["lineend"],
                transform=ax.transData,
                zorder=params["zorder"],
                rasterized=params["raster"],
            )
            ax.add_patch(patch)
