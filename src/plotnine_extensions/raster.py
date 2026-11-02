"""
Per-layer rasterisation, in the spirit of R's ggrastr

Matplotlib's own ``rasterized=True`` renders at the dpi given to
``savefig``, for every rasterised artist in the figure. ``rasterise``
renders one layer into a bitmap at its own dpi and embeds that bitmap in
an otherwise vector figure (PDF, SVG, PS). Axes, text, legends and every
layer you did not rasterise stay vector.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.artist import Artist, allow_rasterization
from matplotlib.transforms import Affine2D
from plotnine.geoms.geom import geom
from plotnine.ggplot import ggplot
from plotnine.layer import layer
from plotnine.stats.stat import stat

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from typing import Any, TypeVar

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase

    T = TypeVar("T")

__all__ = ["RasterGroup", "rasterise", "rasterize"]


class RasterGroup(Artist):
    """
    Draw a set of artists as one embedded bitmap at a fixed dpi

    With a vector backend, the children are drawn into an off-screen Agg
    canvas at ``dpi`` and the result is placed into the vector output with
    its physical size preserved. With a raster backend (PNG, screen) the
    children are drawn directly; the output is a bitmap already.

    Parameters
    ----------
    artists :
        Artists to draw. They must already have their transforms, axes and
        figure set, and must not also be children of an Axes.
    dpi :
        Resolution of the embedded bitmap. `None` uses the resolution
        passed to ``savefig``.
    """

    def __init__(self, artists: Sequence[Artist], dpi: float | None = 300):
        super().__init__()
        self._artists = sorted(artists, key=lambda a: a.get_zorder())
        self.dpi = dpi
        if self._artists:
            self.set_zorder(self._artists[0].get_zorder())
        self.set_in_layout(False)

    def get_children(self) -> list[Artist]:
        return list(self._artists)

    def _draw_children(self, renderer: RendererBase):
        for a in self._artists:
            a.draw(renderer)

    # Decorated so that a mixed-mode renderer left in raster mode by a
    # previous rasterized artist is flushed before we draw our image.
    @allow_rasterization
    def draw(self, renderer: RendererBase):
        if not self.get_visible() or not self._artists:
            return

        if not _is_vector(renderer) or self.dpi is None:
            self._draw_children(renderer)
        elif not renderer.option_scale_image():
            # Cannot scale an embedded bitmap; fall back to matplotlib's
            # own rasterisation at the savefig dpi.
            for a in self._artists:
                a.set_rasterized(True)
            self._draw_children(renderer)
        else:
            self._draw_as_image(renderer)

        self.stale = False

    def _draw_as_image(self, renderer: Any):
        from matplotlib._tight_bbox import process_figure_for_rasterizing
        from matplotlib.backends.backend_agg import RendererAgg

        fig = renderer.figure
        figdpi = renderer._figdpi
        dpi = float(self.dpi)  # pyright: ignore[reportArgumentType]
        width_in, height_in = renderer._width, renderer._height
        restore = renderer._bbox_inches_restore

        agg = RendererAgg(int(width_in * dpi), int(height_in * dpi), dpi)
        fig.dpi = dpi
        if restore:
            restore = process_figure_for_rasterizing(fig, restore, agg)
        try:
            self._draw_children(agg)
        finally:
            fig.dpi = figdpi
            if restore:
                restore = process_figure_for_rasterizing(
                    fig, restore, renderer._vector_renderer, figdpi
                )
                renderer._bbox_inches_restore = restore

        img = np.asarray(agg.buffer_rgba())
        rows = np.flatnonzero(img[..., 3].any(axis=1))
        cols = np.flatnonzero(img[..., 3].any(axis=0))
        if not len(rows):
            return

        r0, r1 = rows[0], rows[-1] + 1
        c0, c1 = cols[0], cols[-1] + 1
        cropped = img[r0:r1, c0:c1]
        h_px, w_px = cropped.shape[:2]
        scale = figdpi / dpi
        height_px = agg.height

        gc = renderer.new_gc()
        gc.set_alpha(1.0)
        renderer.draw_image(
            gc,
            c0 * scale,
            (height_px - r1) * scale,
            cropped[::-1],
            Affine2D().scale(w_px * scale, h_px * scale),
        )
        gc.restore()


def _is_vector(renderer: RendererBase) -> bool:
    from matplotlib.backends.backend_mixed import MixedModeRenderer

    return isinstance(renderer, MixedModeRenderer)


def _wrap_geom(g: geom, dpi: float | None) -> geom:
    """
    Make the geom draw each panel's artists through a RasterGroup
    """
    g._rasterise_dpi = dpi  # pyright: ignore[reportAttributeAccessIssue]
    if "draw_layer" not in vars(g):
        g.draw_layer = _draw_layer.__get__(g)  # pyright: ignore[reportAttributeAccessIssue]
    return g


def _draw_layer(self: geom, data, layout, coord):
    axs: list[Axes] = list(layout.axs)
    before = [set(ax.get_children()) for ax in axs]
    type(self).draw_layer(self, data, layout, coord)

    for ax, prev in zip(axs, before):
        new = [a for a in ax.get_children() if a not in prev]
        if not new:
            continue
        fig = ax.get_figure(root=False)
        for a in new:
            # Detach from the axes' draw list but keep the references that
            # drawing relies on (dpi for marker sizes, axes for clipping).
            a.remove()
            a.axes = ax
            a.set_figure(fig)  # pyright: ignore[reportArgumentType]
        ax.add_artist(RasterGroup(new, self._rasterise_dpi))  # pyright: ignore[reportAttributeAccessIssue]


def _class_name_matches(obj: layer, names: Iterable[str] | None) -> bool:
    if names is None:
        return True
    gname = type(obj.geom).__name__.removeprefix("geom_")
    return gname in {n.removeprefix("geom_") for n in names}


def rasterise(obj: T, dpi: float | None = 300, layers=None) -> T:
    """
    Render a layer as a bitmap inside vector output

    Parameters
    ----------
    obj :
        A geom (e.g. ``geom_point()``), a stat, a layer, a list of any of
        these, or a whole ``ggplot``.
    dpi :
        Resolution of the bitmap. `None` uses the dpi passed to ``save``.
    layers :
        Only for a ``ggplot``: geom names whose layers to rasterise, e.g.
        ``["point", "tile"]``. `None` rasterises every layer.

    Returns
    -------
    :
        The same kind of object, ready to add to a plot. A ``ggplot`` is
        copied; geoms, stats and layers are modified in place.

    Examples
    --------
    ```python
    p = (
        ggplot(df, aes("x", "y"))
        + rasterise(geom_point(alpha=0.3), dpi=300)
        + geom_smooth()  # stays vector
    )
    p.save("fig.pdf")
    ```
    """
    if dpi is not None and dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")

    if isinstance(obj, ggplot):
        p = deepcopy(obj)
        for lyr in p.layers:
            if _class_name_matches(lyr, layers):
                _wrap_geom(lyr.geom, dpi)
        return p  # pyright: ignore[reportReturnType]

    if layers is not None:
        raise TypeError("`layers` only applies when rasterising a ggplot")

    if isinstance(obj, (list, tuple)):
        return type(obj)(rasterise(o, dpi) for o in obj)  # pyright: ignore[reportReturnType]
    if isinstance(obj, layer):
        _wrap_geom(obj.geom, dpi)
        return obj
    if isinstance(obj, geom):
        return _wrap_geom(obj, dpi)  # pyright: ignore[reportReturnType]
    if isinstance(obj, stat):
        # plotnine 0.15 builds layers with stat.to_layer(); later
        # versions with layer(stat=...)
        lyr = obj.to_layer() if hasattr(obj, "to_layer") else layer(stat=obj)
        _wrap_geom(lyr.geom, dpi)
        return lyr  # pyright: ignore[reportReturnType]

    raise TypeError(f"Cannot rasterise an object of type {type(obj)}")


rasterize = rasterise
