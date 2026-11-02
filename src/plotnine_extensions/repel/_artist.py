"""
Matplotlib artist that places repelled labels at draw time

Placement happens inside ``draw`` with the renderer that is producing
the output, so label sizes and positions are measured in the final
figure: after plotnine's layout manager has sized the panels, at the dpi
of the file being written. This is the property that makes ggrepel
reliable and that a one-off adjustment at layer-draw time lacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from warnings import warn

import numpy as np
from matplotlib.artist import Artist, allow_rasterization
from matplotlib.collections import LineCollection
from matplotlib.patches import FancyArrowPatch
from matplotlib.transforms import IdentityTransform
from plotnine.exceptions import PlotnineWarning

from ._solver import count_overlaps, repel

if TYPE_CHECKING:
    from typing import Any

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


@dataclass
class RepelSettings:
    box_padding: float
    point_padding: float
    point_radius: float
    min_segment_length: float
    segment_color: Any
    segment_linewidth: float
    segment_linestyle: Any
    arrow: dict[str, Any] | None
    force: float
    force_pull: float
    max_iter: int
    max_time: float
    max_overlaps: float
    direction: str
    seed: int | None
    xlim: tuple[float | None, float | None] | None
    ylim: tuple[float | None, float | None] | None
    label_pad: np.ndarray = field(default_factory=lambda: np.zeros(0))
    """Per-label padding of the label box, in points"""


@dataclass
class _Layout:
    key: tuple
    keep: np.ndarray
    centres: np.ndarray
    converged: bool


class RepelLabels(Artist):
    """
    Text labels pushed off each other and off their data points

    Parameters
    ----------
    ax :
        Axes whose data transform locates the points.
    points :
        (m, 2) data coordinates of every point in the panel. All of them
        repel labels, labelled or not.
    label_index :
        For each text, the row of its point in ``points``.
    nudged :
        (n, 2) data coordinates each label starts from.
    texts :
        Text artists, not added to any axes.
    settings :
        Placement and segment options.
    """

    def __init__(
        self,
        ax: Axes,
        points: np.ndarray,
        label_index: np.ndarray,
        nudged: np.ndarray,
        texts: list[Text],
        settings: RepelSettings,
    ):
        super().__init__()
        self._ax = ax
        self._points = np.asarray(points, float).reshape(-1, 2)
        self._label_index = np.asarray(label_index, int)
        self._nudged = np.asarray(nudged, float).reshape(-1, 2)
        self._texts = texts
        self.settings = settings
        self._layout: _Layout | None = None
        self.set_in_layout(False)
        for t in texts:
            t.set_transform(IdentityTransform())
            t.set_clip_on(False)
            t.set_horizontalalignment("center")
            t.set_verticalalignment("center")
            t.set_rotation_mode("anchor")

    def get_children(self) -> list[Artist]:
        return list(self._texts)

    @property
    def last_layout(self) -> _Layout | None:
        """
        The placement computed by the most recent draw
        """
        return self._layout

    def _bounds(self) -> tuple[float, float, float, float]:
        """
        Region (display units) that labels must stay within
        """
        x0, y0, x1, y1 = self._ax.bbox.extents
        edges = [[x0, x1], [y0, y1]]
        trans = self._ax.transData
        for k, lim in enumerate((self.settings.xlim, self.settings.ylim)):
            if lim is None:
                continue
            panel = list(edges[k])
            mapped = []
            for v in lim:
                if v is None:
                    mapped.append(None)
                    continue
                xy = [[v, 0.0]] if k == 0 else [[0.0, v]]
                mapped.append(float(trans.transform(xy)[0, k]))
            # A reversed scale maps the lower limit to the higher pixel
            lo_v, hi_v = mapped
            unit = trans.transform([[1.0, 1.0]])[0, k] - trans.transform(
                [[0.0, 0.0]]
            )[0, k]
            if unit < 0:
                lo_v, hi_v = hi_v, lo_v
            edges[k] = [
                max(panel[0], lo_v) if lo_v is not None else panel[0],
                min(panel[1], hi_v) if hi_v is not None else panel[1],
            ]
        (x0, x1), (y0, y1) = edges
        return x0, x1, y0, y1

    def _measure(self, renderer: RendererBase) -> tuple[np.ndarray, np.ndarray]:
        """
        Box sizes used for repulsion, and text sizes used for segments
        """
        pt = renderer.points_to_pixels(1.0)
        text_size = np.zeros((len(self._texts), 2))
        for i, t in enumerate(self._texts):
            t.set_position((0, 0))
            bb = t.get_window_extent(renderer)
            text_size[i] = bb.width, bb.height
        if len(self.settings.label_pad):
            text_size += 2 * self.settings.label_pad[:, None] * pt
        box = text_size + 2 * self.settings.box_padding * pt
        return box, text_size

    def _compute(self, renderer: RendererBase) -> _Layout:
        s = self.settings
        trans = self._ax.transData
        pts = trans.transform(self._points) if len(self._points) else self._points
        anchors = pts[self._label_index]
        start = trans.transform(self._nudged) if len(self._nudged) else anchors
        bounds = self._bounds()
        box, text_size = self._measure(renderer)
        pt = renderer.points_to_pixels(1.0)
        radius = np.full(len(pts), (s.point_radius + s.point_padding) * pt)

        key = (
            np.round(pts, 2).tobytes(),
            np.round(start, 2).tobytes(),
            np.round(box, 2).tobytes(),
            tuple(np.round(bounds, 2)),
        )
        if self._layout is not None and self._layout.key == key:
            return self._layout

        # Points outside the panel (e.g. a zoomed coord) get no label.
        # Test against the panel, not the label region: with xlim/ylim a
        # point may sit outside the region its label must move into.
        x0, y0, x1, y1 = self._ax.bbox.extents
        inside = (
            (anchors[:, 0] >= x0 - 0.5)
            & (anchors[:, 0] <= x1 + 0.5)
            & (anchors[:, 1] >= y0 - 0.5)
            & (anchors[:, 1] <= y1 + 0.5)
            & np.isfinite(anchors).all(axis=1)
        )
        finite_pts = np.isfinite(pts).all(axis=1)

        keep = inside.copy()
        centres = start.copy()
        converged = True
        idx = np.flatnonzero(inside)
        obstacles = pts[finite_pts]
        obstacle_r = radius[finite_pts]
        # Points are renumbered after dropping non-finite ones
        renum = np.cumsum(finite_pts) - 1

        def solve(rows, from_):
            return repel(
                anchors[rows],
                box[rows],
                obstacles,
                obstacle_r,
                bounds,
                start=from_,
                force=s.force,
                force_pull=s.force_pull,
                direction=s.direction,
                max_iter=s.max_iter,
                max_time=s.max_time,
                seed=s.seed,
            )

        if len(idx):
            res = solve(idx, start[idx])
            centres[idx] = res.centres
            converged = res.converged

            # Labels that could not be placed clear of the crowd are
            # dropped, then the rest are placed again without them.
            sub_keep = count_overlaps(
                res.centres,
                box[idx] / 2,
                obstacles,
                obstacle_r,
                renum[self._label_index[idx]],
                s.max_overlaps,
            )
            n_dropped = int((~sub_keep).sum())
            if n_dropped:
                warn(
                    f"{n_dropped} labels not drawn because, after placement, "
                    f"they overlap more than max_overlaps={s.max_overlaps} "
                    "other labels or points. Increase max_overlaps or "
                    "max_time to keep them.",
                    PlotnineWarning,
                    stacklevel=2,
                )
                keep[idx[~sub_keep]] = False
                idx = idx[sub_keep]
                if len(idx):
                    res = solve(idx, res.centres[sub_keep])
                    centres[idx] = res.centres
                    converged = res.converged

        self._layout = _Layout(key, keep, centres, converged)
        self._text_size = text_size
        self._anchors = anchors
        self._radius_px = (s.point_radius + s.point_padding) * pt
        return self._layout

    def _segments(self, renderer: RendererBase, layout: _Layout):
        """
        Line from each point to the edge of its label's text box
        """
        s = self.settings
        pt = renderer.points_to_pixels(1.0)
        idx = np.flatnonzero(layout.keep)
        a = self._anchors[idx]
        c = layout.centres[idx]
        half = self._text_size[idx] / 2 + 0.5 * pt
        d = a - c

        # Anchors inside their own box get no segment
        inside = (np.abs(d[:, 0]) <= half[:, 0]) & (np.abs(d[:, 1]) <= half[:, 1])

        # Scale the centre-to-anchor vector so it ends on the box edge
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.minimum(
                np.where(d[:, 0] != 0, half[:, 0] / np.abs(d[:, 0]), np.inf),
                np.where(d[:, 1] != 0, half[:, 1] / np.abs(d[:, 1]), np.inf),
            )
        end = c + d * np.clip(t, 0, 1)[:, None]

        seg = a - end
        length = np.hypot(seg[:, 0], seg[:, 1])
        with np.errstate(divide="ignore", invalid="ignore"):
            unit = seg / length[:, None]
        start = a - unit * self._radius_px
        visible_len = length - self._radius_px
        ok = (
            ~inside
            & (visible_len > s.min_segment_length * pt)
            & np.isfinite(start).all(axis=1)
        )
        return idx[ok], start[ok], end[ok]

    @allow_rasterization
    def draw(self, renderer: RendererBase):
        if not self.get_visible() or not self._texts:
            return

        fig = self.get_figure(root=False)
        for t in self._texts:
            if t.get_figure(root=False) is None:
                t.set_figure(fig)

        layout = self._compute(renderer)
        s = self.settings
        lab, start, end = self._segments(renderer, layout)

        if len(lab):
            colors = [
                s.segment_color
                if s.segment_color is not None
                else self._texts[i].get_color()
                for i in lab
            ]
            lw = s.segment_linewidth
            if s.arrow is None:
                lc = LineCollection(
                    np.stack([start, end], axis=1),
                    colors=colors,
                    linewidths=lw,
                    linestyles=s.segment_linestyle,
                    transform=IdentityTransform(),
                    zorder=self.get_zorder(),
                    capstyle="butt",
                )
                lc.set_figure(self.get_figure(root=False))
                lc.draw(renderer)
            else:
                arrow = {"arrowstyle": "-|>", "mutation_scale": 8} | s.arrow
                for col, p0, p1 in zip(colors, end, start):
                    fa = FancyArrowPatch(
                        posA=tuple(p0),
                        posB=tuple(p1),
                        color=col,
                        linewidth=lw,
                        linestyle=s.segment_linestyle,
                        shrinkA=0,
                        shrinkB=0,
                        transform=IdentityTransform(),
                        **arrow,
                    )
                    fa.set_figure(self.get_figure(root=False))
                    fa.draw(renderer)

        for i in np.flatnonzero(layout.keep):
            t = self._texts[i]
            t.set_position(tuple(layout.centres[i]))
            t.draw(renderer)

        self.stale = False
