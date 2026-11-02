"""
Hexagonal binning, as in ggplot2's geom_hex / stat_bin_hex
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from plotnine._utils import SIZE_FACTOR, to_rgba
from plotnine.geoms.geom import geom
from plotnine.geoms.geom_polygon import geom_polygon
from plotnine.mapping.evaluation import after_stat
from plotnine.stats.stat import stat

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view

__all__ = ["geom_hex", "hex_bins", "stat_bin_hex"]

# Vertices of a pointy-topped hexagon of width 1 and row spacing 1
# (height 4/3), relative to its centre
_HEX = np.array(
    [[0, 2 / 3], [0.5, 1 / 3], [0.5, -1 / 3], [0, -2 / 3], [-0.5, -1 / 3], [-0.5, 1 / 3]]
)


def hex_bins(x, y, binwidth: tuple[float, float], origin=(0.0, 0.0), weight=None):
    """
    Assign points to a hexagonal grid

    Hexagons are pointy-topped. ``binwidth[0]`` is the horizontal distance
    between neighbouring centres in a row; ``binwidth[1]`` the vertical
    distance between centres in the same column (rows alternate, offset by
    half a hexagon).

    Returns
    -------
    pandas.DataFrame
        One row per occupied hexagon: ``x``, ``y`` (centre), ``count`` (sum
        of weights).
    """
    bx, by = binwidth
    ry = by / 2  # vertical distance between consecutive (offset) rows
    u = (np.asarray(x, float) - origin[0]) / bx
    v = (np.asarray(y, float) - origin[1]) / ry
    w = np.ones(len(u)) if weight is None else np.asarray(weight, float)

    # Even rows: centres at integer u; odd rows: at half-integer u.
    k_even = 2 * np.round(v / 2)
    i_even = np.round(u)
    k_odd = 2 * np.floor(v / 2) + 1
    i_odd = np.floor(u) + 0.5
    # Nearest centre in the space where the lattice is regular
    # (row spacing sqrt(3)/2 of the column spacing)
    s = np.sqrt(3) / 2
    d_even = (u - i_even) ** 2 + ((v - k_even) * s) ** 2
    d_odd = (u - i_odd) ** 2 + ((v - k_odd) * s) ** 2
    odd = d_odd < d_even
    ci = np.where(odd, i_odd, i_even)
    ck = np.where(odd, k_odd, k_even)

    df = pd.DataFrame({"ci": ci, "ck": ck, "w": w})
    out = df.groupby(["ci", "ck"], sort=True)["w"].sum().reset_index()
    return pd.DataFrame(
        {
            "x": origin[0] + out["ci"].to_numpy() * bx,
            "y": origin[1] + out["ck"].to_numpy() * ry,
            "count": out["w"].to_numpy(),
        }
    )


class stat_bin_hex(stat):
    """
    Count points in hexagonal bins

    Parameters
    ----------
    bins : int or (int, int), default=30
        Number of hexagons across the x (and y) range of the data.
    binwidth : (float, float), optional
        Horizontal distance between neighbouring centres and vertical
        distance between centres in the same column. Overrides `bins`.

    Notes
    -----
    Computed variables: ``count`` (points, or summed `weight`, per
    hexagon), ``density`` (count as a fraction of the panel total),
    ``width`` and ``height`` (the bin widths).
    """

    REQUIRED_AES = {"x", "y"}
    DEFAULT_AES = {"fill": after_stat("count"), "weight": None}
    DEFAULT_PARAMS = {
        "geom": "hex",
        "position": "identity",
        "na_rm": False,
        "bins": 30,
        "binwidth": None,
    }
    CREATES = {"count", "density", "width", "height", "xmin", "xmax", "ymin", "ymax"}
    DROPPED_AES = ["weight"]

    def setup_params(self, data: pd.DataFrame):
        params = dict(self.params)
        if params["binwidth"] is None:
            bins = params["bins"]
            nx, ny = (bins, bins) if np.isscalar(bins) else bins
            rx = np.ptp(data["x"].to_numpy(float)) or 1.0
            ry = np.ptp(data["y"].to_numpy(float)) or 1.0
            params["binwidth"] = (rx / nx, ry / ny)
        bx, by = params["binwidth"]
        if bx <= 0 or by <= 0:
            raise ValueError(f"binwidth must be positive, got {params['binwidth']}")
        params["origin"] = (
            float(np.nanmin(data["x"])),
            float(np.nanmin(data["y"])),
        )
        return params

    def compute_layer(self, data, layout):
        # The grid is shared across panels and groups so hexagons line up
        self.params = self.setup_params(data)
        return super().compute_layer(data, layout)

    def compute_panel(self, data: pd.DataFrame, scales):
        params = self.params
        weight = data["weight"] if "weight" in data else None
        if weight is not None and weight.isna().all():
            weight = None
        out = hex_bins(
            data["x"], data["y"], params["binwidth"], params["origin"], weight
        )
        bx, by = params["binwidth"]
        out["density"] = out["count"] / out["count"].sum()
        out["width"], out["height"] = bx, by
        # Hexagon extents, so the scales cover whole hexagons
        out["xmin"], out["xmax"] = out["x"] - bx / 2, out["x"] + bx / 2
        out["ymin"], out["ymax"] = out["y"] - by / 3, out["y"] + by / 3
        out["PANEL"] = data["PANEL"].iloc[0]
        out["group"] = -1
        return out


class geom_hex(geom):
    """
    Hexagons

    Draws hexagons centred on (`x`, `y`) with the bin widths of
    `stat_bin_hex`, its default stat. Fill is the count by default.

    Parameters
    ----------
    stat : str, default="bin_hex"
        Use ``"identity"`` for precomputed centres, and map or set the bin
        widths: ``aes(width="w", height="h")`` or ``width=0.5,
        height=0.5``.
    """

    DEFAULT_AES = {
        "alpha": 1,
        "color": None,
        "fill": "#595959",
        "linetype": "solid",
        "size": 0.5,
        "width": None,
        "height": None,
    }
    REQUIRED_AES = {"x", "y"}
    DEFAULT_PARAMS = {
        "stat": "bin_hex",
        "position": "identity",
        "na_rm": False,
    }
    draw_legend = staticmethod(geom_polygon.draw_legend)

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        from matplotlib.collections import PolyCollection

        if not len(data):
            return
        for col in ("width", "height"):
            if col not in data or data[col].isna().any():
                raise ValueError(
                    f"geom_hex needs a {col!r}: use the default stat_bin_hex, "
                    f"or map it with aes({col}=...) or set {col}=..."
                )
        data = coord.transform(data, panel_params)
        cx = data["x"].to_numpy(float)[:, None]
        cy = data["y"].to_numpy(float)[:, None]
        bx = data["width"].to_numpy(float)[:, None]
        # _HEX has row spacing 1; a column spacing of `height` is 2 rows
        ry = data["height"].to_numpy(float)[:, None] / 2
        xs = cx + _HEX[None, :, 0] * bx
        ys = cy + _HEX[None, :, 1] * ry
        verts = np.stack([xs, ys], axis=-1)

        edge = data["color"]
        col = PolyCollection(
            verts,
            facecolors=to_rgba(data["fill"], data["alpha"]),
            edgecolors="none" if edge.isna().all() else list(edge),
            linewidths=data["size"] * SIZE_FACTOR,
            linestyles=data["linetype"],
            zorder=self.params["zorder"],
            rasterized=self.params["raster"],
        )
        ax.add_collection(col)
