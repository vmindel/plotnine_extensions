"""
Several scales for the same aesthetic, in the spirit of R's ggnewscale

```python
(
    ggplot(df)
    + geom_tile(aes("x", "y", fill="density"))
    + new_scale_fill()
    + geom_point(aes("x", "y", fill="cluster"), shape="o")
)
```

`new_scale_fill()` closes the fill scale of the layers added so far.
Those layers keep the fill scale that was in the plot when the
new scale was added (or get a default one); layers and fill scales added
afterwards form a new, independent scale with its own legend.

How it works, as in ggnewscale: when added, the aesthetic of every
earlier layer, scale, label and guide is renamed, e.g. ``fill`` to
``fill_new1``. The renamed column is trained and mapped by its own
scale; after mapping, the layer renames it back so the geom draws it as
``fill``. For legends, the layer presents the renamed aesthetic to the
guides.
"""

from __future__ import annotations

import re
from copy import copy
from typing import TYPE_CHECKING

import pandas as pd
import plotnine.guides  # registers the guides  # noqa: F401
from plotnine._utils.registry import Registry
from plotnine.exceptions import PlotnineError
from plotnine.guides.guide import guide as guide_base
from plotnine.iapi import labels_view
from plotnine.layer import add_group, layer
from plotnine.mapping.aes import (
    SCALED_AESTHETICS,
    aes,
    make_labels,
    rename_aesthetics,
)
from plotnine.mapping.evaluation import evaluate
from plotnine.scales.scales import make_scale

if TYPE_CHECKING:
    from typing import Any

    from plotnine import ggplot
    from plotnine.geoms.geom import geom
    from plotnine.scales.scales import Scales

__all__ = [
    "new_scale",
    "new_scale_color",
    "new_scale_colour",
    "new_scale_fill",
]

# Scaled aesthetics that can be split; x and y have one scale per panel
NEW_SCALE_AESTHETICS = frozenset(SCALED_AESTHETICS - {"x", "y", "colour"})


class new_scale:
    """
    Start a new scale for one or more aesthetics

    Layers and scales for `aesthetics` added before this keep the old
    scale; those added after it use a new, independent one. Each scale
    gets its own legend.

    Parameters
    ----------
    *aesthetics :
        Names of the aesthetics, e.g. ``"color"``, ``"fill"``,
        ``"size"``, ``"shape"``, ``"alpha"``, ``"linetype"``,
        ``"stroke"``.

    Notes
    -----
    Add a scale for the old layers before `new_scale` and one for the
    new layers after it, as in ggnewscale. The same goes for
    ``labs(...)`` and ``guides(...)`` for the aesthetic: whatever is in
    the plot when `new_scale` is added belongs to the old scale.

    A mapping of the aesthetic in ``ggplot(aes(...))`` is inherited by
    every layer: earlier layers map it on the old scale, later layers on
    the new one. Map it in each layer instead.

    Two legends with the same title and the same labels are merged into
    one, as for any two scales; give the scales different names.

    The aesthetics of earlier layers are renamed internally (``fill``
    becomes ``fill_new1``), so ``after_scale()`` expressions in those
    layers see the renamed column.
    """

    def __init__(self, *aesthetics: str):
        if not aesthetics:
            raise ValueError("new_scale needs at least one aesthetic")
        names = rename_aesthetics(list(aesthetics))
        bad = [ae for ae in names if ae not in NEW_SCALE_AESTHETICS]
        if bad:
            raise ValueError(
                f"Cannot start a new scale for {bad}. Choose from "
                f"{sorted(NEW_SCALE_AESTHETICS)}."
            )
        # Keep the order, drop repeats
        self.aesthetics = list(dict.fromkeys(names))

    def __radd__(self, plot: ggplot) -> ggplot:
        for ae in self.aesthetics:
            _bump(plot, ae)
        return plot

    def __repr__(self) -> str:
        args = ", ".join(repr(ae) for ae in self.aesthetics)
        return f"new_scale({args})"


def new_scale_color() -> new_scale:
    """
    Start a new color scale; see `new_scale`
    """
    return new_scale("color")


def new_scale_fill() -> new_scale:
    """
    Start a new fill scale; see `new_scale`
    """
    return new_scale("fill")


new_scale_colour = new_scale_color


def _bump(plot: ggplot, ae: str):
    """
    Rename `ae` in everything the plot holds so far
    """
    new = f"{ae}_new{_next_index(plot, ae)}"

    # The guide given by guides(ae=...) belongs to the old scale
    guide = getattr(plot.guides, ae, None)
    has_guide = guide is not None
    if has_guide:
        setattr(plot.guides, ae, None)
        guide = _scale_guide(guide)

    for sc in plot.scales:
        if ae in sc.aesthetics:
            sc.aesthetics = [new if a == ae else a for a in sc.aesthetics]
            if has_guide:
                sc.guide = guide
            sc.guide = _widen_guide(sc.guide)

    # Always set, so that a guide for the renamed scale finds a label
    setattr(plot.labels, new, getattr(plot.labels, ae))
    setattr(plot.labels, ae, None)

    for lyr in plot.layers:
        if not isinstance(lyr, _NewScaleLayer):
            lyr = _adopt(lyr)
        if ae not in lyr._newscale_renames:
            lyr._newscale_renames[ae] = new
            if has_guide:
                lyr._newscale_guides[new] = guide


def _next_index(plot: ggplot, ae: str) -> int:
    pattern = re.compile(rf"^{ae}_new(\d+)$")
    used = [0]
    for lyr in plot.layers:
        for name in getattr(lyr, "_newscale_renames", {}).values():
            if m := pattern.match(name):
                used.append(int(m.group(1)))
    for sc in plot.scales:
        for name in sc.aesthetics:
            if m := pattern.match(name):
                used.append(int(m.group(1)))
    return max(used) + 1


def _scale_guide(guide: Any) -> Any:
    # guides() accepts "none"/False to remove a guide; a scale wants None
    return None if guide in ("none", False) else guide


# A layer is adopted by swapping its class for a subclass that mixes in
# the renaming. Subclasses of layer get a subclass made on the fly.
_ADOPTED: dict[type, type] = {}


def _adopt(lyr: layer) -> _NewScaleLayer:
    cls = type(lyr)
    if cls not in _ADOPTED:
        _ADOPTED[cls] = (
            _NewScaleLayer
            if cls is layer
            else type(cls.__name__, (_NewScaleLayer, cls), {})
        )
    lyr.__class__ = _ADOPTED[cls]
    lyr._newscale_renames = {}
    lyr._newscale_guides = {}
    lyr._newscale_saved = None
    return lyr  # pyright: ignore[reportReturnType]


# No guide was given with guides() for the aesthetic
_NO_GUIDE = object()


def _rename_keys(d: dict[str, Any], renames: dict[str, str]) -> dict:
    return {renames.get(k, k): v for k, v in d.items()}


def _ensure_scale(
    scales: Scales,
    name: str,
    base: str,
    series: pd.Series,
    guide: Any = _NO_GUIDE,
):
    """
    Add a default scale for the renamed aesthetic `name`
    """
    if scales.get_scales(name) is not None:
        return
    try:
        sc = make_scale(base, series)
    except PlotnineError:
        return
    sc.aesthetics = [name]
    if guide is not _NO_GUIDE:
        sc.guide = guide
    sc.guide = _widen_guide(sc.guide)
    scales.append(sc)


class _BaseNames(set):
    """
    Set of aesthetics that also contains their renamed versions
    """

    def __contains__(self, name: object) -> bool:
        if isinstance(name, str):
            name = _SUFFIX.sub("", name)
        return super().__contains__(name)


_SUFFIX = re.compile(r"_new\d+$")

# Guides that accept only some aesthetics (guide_colorbar: color and
# fill) check the scale's aesthetic name. The renamed scales get a
# subclass that accepts the renamed names. It is registered so that
# scale.guide can stay a string and each draw makes a fresh guide.
# "newscale_" goes in front: plotnine takes the theme kind of a guide
# from the last word of its class name.
_WIDE_GUIDES: dict[str, type] = {}


def _widen_guide(g: Any) -> Any:
    if isinstance(g, guide_base):
        if "any" not in g.available_aes:
            g.available_aes = _BaseNames(g.available_aes)
        return g
    if not isinstance(g, str) or g.startswith("newscale_"):
        return g

    cls = Registry[f"guide_{g}"]
    if "any" in cls().available_aes:
        return g
    if g not in _WIDE_GUIDES:
        # __init__, not __post_init__: a dataclass's generated __init__
        # calls __post_init__ only if the decorated class had one, and
        # guide_colorbar has none in plotnine's development branch
        def __init__(self, *args, **kwargs):
            cls.__init__(self, *args, **kwargs)
            self.available_aes = _BaseNames(self.available_aes)

        # Registry holds weak references; _WIDE_GUIDES keeps it alive.
        # A module attribute, so that drawn plots (whose guides are
        # instances of it) can be pickled.
        name = f"guide_newscale_{g}"
        wide = type(name, (cls,), {"__init__": __init__})
        wide.__module__ = __name__
        globals()[name] = _WIDE_GUIDES[g] = wide
    return f"newscale_{g}"


# Made at import so that pickled plots load in a fresh process
_widen_guide("colorbar")


class _NewScaleLayer(layer):
    """
    Mixin for a layer whose aesthetics have been moved to older scales

    `_newscale_renames` maps an aesthetic to its renamed version for
    this layer, e.g. ``{"fill": "fill_new1"}``.
    """

    _newscale_renames: dict[str, str]
    _newscale_guides: dict[str, Any]
    # (geom, stat, show_legend) while the layer is set up for the legends
    _newscale_saved: tuple | None

    @property
    def _renames(self) -> dict[str, str]:
        # Aesthetics set as parameters are constants, not mapped
        params = self.geom.aes_params
        return {
            k: v for k, v in self._newscale_renames.items() if k not in params
        }

    @property
    def _base_names(self) -> dict[str, str]:
        return {v: k for k, v in self._renames.items()}

    def _to_base(self, data: pd.DataFrame) -> pd.DataFrame:
        base = {k: v for k, v in self._base_names.items() if v not in data}
        return data.rename(columns=base) if base else data

    def _to_renamed(self, data: pd.DataFrame) -> pd.DataFrame:
        renames = {k: v for k, v in self._renames.items() if v not in data}
        return data.rename(columns=renames) if renames else data

    def _add_default_scales(self, plot: ggplot, data: pd.DataFrame, cols):
        base = self._base_names
        plain = {c: c for c in cols if c not in base}
        plot.scales.add_defaults(data, aes(**plain))
        for c in cols:
            if c in base:
                _ensure_scale(
                    plot.scales,
                    c,
                    base[c],
                    data[c],
                    self._newscale_guides.get(c, _NO_GUIDE),
                )

    # Build steps -------------------------------------------------------

    def update_labels(self, target):
        # As layer.update_labels for the aesthetics that keep their
        # names. plotnine 0.15 passes the plot, later versions its
        # labels. The renamed aesthetics are labelled in setup, once the
        # layer has inherited the plot mapping.
        labels = target if isinstance(target, labels_view) else target.labels
        skip = self._renames.keys() | self._base_names.keys()
        for m in (self.mapping, self.stat.DEFAULT_AES):
            plain = {k: v for k, v in m.items() if k not in skip}
            labels.add_defaults(make_labels(plain))

    def setup(self, plot: ggplot):
        self._newscale_leave_legend()
        super().setup(plot)
        # labels_view has no fields for the renamed aesthetics, so their
        # labels are attributes. A label set with labs() before
        # new_scale was moved there already and wins.
        base = self._base_names
        stat = _rename_keys(self.stat.DEFAULT_AES, self._renames)
        for m in (self.mapping, stat):
            for k, v in m.items():
                if k in base and getattr(plot.labels, k, None) is None:
                    label = make_labels({base[k]: v})
                    setattr(plot.labels, k, getattr(label, base[k]))

    def _make_layer_mapping(self, plot_mapping: aes):
        super()._make_layer_mapping(plot_mapping)
        self.mapping = aes(**_rename_keys(self.mapping, self._renames))

    def compute_aesthetics(self, plot: ggplot):
        # As layer.compute_aesthetics, with default scales for the
        # renamed aesthetics and groups that include them
        evaled = evaluate(self.mapping._starting, self.data, plot.environment)
        self._add_default_scales(plot, evaled, evaled.columns)

        if len(self.data) == 0 and len(evaled) > 0:
            evaled["PANEL"] = 1
        else:
            evaled["PANEL"] = self.data["PANEL"]

        # add_group only looks at known aesthetics
        plain = add_group(evaled.rename(columns=self._base_names))
        if len(plain):
            evaled["group"] = plain["group"]
        self.data = evaled.sort_values("PANEL", kind="mergesort")

    # Stats, geom setup and positions see the usual aesthetic names
    # (position_jitterdodge looks for fill and color, for instance)

    def compute_statistic(self, layout):
        self.data = self._to_base(self.data)
        super().compute_statistic(layout)
        self.data = self._to_renamed(self.data)

    def setup_data(self):
        self.data = self._to_base(self.data)
        super().setup_data()
        self.data = self._to_renamed(self.data)

    def compute_position(self, layout):
        self.data = self._to_base(self.data)
        super().compute_position(layout)
        self.data = self._to_renamed(self.data)

    def map_statistic(self, plot: ggplot):
        # As layer.map_statistic, with the stat's default calculated
        # aesthetics renamed
        stat_defaults = _rename_keys(self.stat.DEFAULT_AES, self._renames)
        calculated = (
            aes(**stat_defaults)._calculated | self.mapping._calculated
        )
        if not len(self.data) or not calculated:
            return

        data = plot.scales.inverse_df(self.data)
        stat_data = evaluate(calculated, data, plot.environment)
        columns = data.columns.difference(stat_data.columns)
        data = pd.concat([data[columns], stat_data], axis=1)
        self.data = plot.scales.transform_df(data)
        self._add_default_scales(plot, self.data, stat_data.columns)

    def use_defaults(
        self,
        data: pd.DataFrame,
        aes_modifiers: dict[str, Any],
        scales: Scales | None = None,
    ) -> pd.DataFrame:
        # Called after the scales have mapped the data, and for the
        # legend keys. From here on the geom sees its own aesthetics.
        base = self._base_names
        if base:
            # A constant set as a parameter wins over a mapped column
            clash = [c for c in base if c in data and base[c] in data]
            data = data.drop(columns=clash).rename(columns=base)
            aes_modifiers = _rename_keys(aes_modifiers, base)
            if scales is not None:
                self.data = data
        return super().use_defaults(data, aes_modifiers, scales)

    def draw(self, layout, coord):
        super().draw(layout, coord)
        self._newscale_enter_legend()

    # Legends -----------------------------------------------------------
    #
    # A guide decides which layers contribute to it from the layer's
    # mapping, its stat's default aesthetics and its geom's aesthetics.
    # The guides are built after the layers are drawn; from then until
    # the next build, the geom and stat present the renamed aesthetics.

    def _newscale_enter_legend(self):
        renames = self._renames
        if not renames or self._newscale_saved is not None:
            return
        self._newscale_saved = (self.geom, self.stat, self.show_legend)
        self.geom = _legend_geom(self.geom, renames)
        stat = copy(self.stat)
        stat.DEFAULT_AES = _rename_keys(self.stat.DEFAULT_AES, renames)
        self.stat = stat
        if isinstance(self.show_legend, dict):
            self.show_legend = _rename_keys(
                rename_aesthetics(dict(self.show_legend)), renames
            )

    def _newscale_leave_legend(self):
        if self._newscale_saved is not None:
            self.geom, self.stat, self.show_legend = self._newscale_saved
            self._newscale_saved = None

    def __getstate__(self):
        # Pickle the real geom and stat, not the legend copies
        state = self.__dict__.copy()
        if (saved := state.get("_newscale_saved")) is not None:
            state["geom"], state["stat"], state["show_legend"] = saved
            state["_newscale_saved"] = None
        return state


def _legend_geom(g: geom, renames: dict[str, str]) -> geom:
    """
    Copy of geom that lists the renamed aesthetics

    Instance attributes shadow the class ones. A subclass would not do:
    plotnine registers every geom class by name, and a subclass called
    geom_point would replace the real one in the registry.
    """
    proxy = copy(g)
    proxy.DEFAULT_AES = _rename_keys(g.DEFAULT_AES, renames)
    proxy.REQUIRED_AES = {renames.get(a, a) for a in g.REQUIRED_AES}
    names = {renames.get(a, a) for a in g.aesthetics()}
    proxy.aesthetics = lambda: set(names)  # a classmethod on geom
    return proxy
