"""
Significance brackets, in the spirit of R's ggsignif and ggpubr
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from plotnine._utils import SIZE_FACTOR, to_rgba
from plotnine.geoms.geom import geom
from plotnine.geoms.geom_path import geom_path
from plotnine.stats.stat import stat

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view

__all__ = ["format_p", "geom_bracket", "p_adjust", "stat_compare_means"]

TESTS = ("t-test", "student", "mann-whitney")
ADJUSTMENTS = ("holm", "bh", "bonferroni")

# p-value thresholds for stars, as in ggpubr
_STARS = ((1e-4, "****"), (1e-3, "***"), (1e-2, "**"), (0.05, "*"))


def p_adjust(p: Sequence[float], method: str | None = "holm") -> np.ndarray:
    """
    Adjust p-values for multiple testing

    Parameters
    ----------
    p : sequence of float
    method : {"holm", "bh", "bonferroni"} or None
        Holm's step-down (controls the family-wise error rate), Benjamini
        and Hochberg's false discovery rate, Bonferroni, or none.
    """
    p = np.asarray(p, float)
    n = len(p)
    if method is None or n <= 1:
        return p.copy()
    if method not in ADJUSTMENTS:
        raise ValueError(f"p_adjust must be one of {ADJUSTMENTS} or None, got {method!r}")
    if method == "bonferroni":
        return np.minimum(p * n, 1)
    order = np.argsort(p)
    ranked = p[order]
    if method == "holm":
        adj = np.maximum.accumulate((n - np.arange(n)) * ranked)
    else:  # bh
        adj = np.minimum.accumulate((n / np.arange(n, 0, -1)) * ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1)
    return out


def format_p(p: float, label: str = "stars", prefix: str = "p") -> str:
    """
    Text for a p-value: stars (``"ns"`` above 0.05) or ``"p = 0.012"``
    """
    if label == "stars":
        for cut, stars in _STARS:
            if p <= cut:
                return stars
        return "ns"
    if label == "p":
        if p < 1e-3:
            mant, exp = f"{p:.1e}".split("e")
            return f"{prefix} = {mant}e{int(exp)}"
        return f"{prefix} = {p:.2g}"
    raise ValueError(f'label must be "stars" or "p", got {label!r}')


def _test(a: np.ndarray, b: np.ndarray, method: str, paired: bool) -> float:
    from scipy import stats

    if paired:
        if len(a) != len(b):
            raise ValueError(
                f"paired tests need groups of equal size, got {len(a)} and {len(b)}"
            )
        if method in ("t-test", "student"):
            return float(stats.ttest_rel(a, b).pvalue)
        return float(stats.wilcoxon(a, b).pvalue)
    if method == "t-test":
        return float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    if method == "student":
        return float(stats.ttest_ind(a, b, equal_var=True).pvalue)
    return float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)


def _x_levels(scale) -> list[str] | None:
    limits = getattr(scale, "final_limits", None)
    if limits is None or callable(limits):
        try:
            limits = scale.get_limits()
        except Exception:
            return None
    if limits is None or len(limits) == 0 or not isinstance(limits[0], str):
        return None
    return [str(x) for x in limits]


def _resolve(name, levels: list[str] | None, kind: str):
    """Position (1-based) of a category name, or a number given as is."""
    if isinstance(name, (int, float, np.integer, np.floating)):
        return float(name)
    if levels is None or str(name) not in levels:
        raise ValueError(f"{kind} {name!r} is not one of {levels}")
    return float(levels.index(str(name)) + 1)


class stat_compare_means(stat):
    """
    Test differences between groups and place significance brackets

    Tests run on the raw observations of each group, in each panel.

    Parameters
    ----------
    comparisons : list of (str, str), optional
        Pairs to compare, by category name (x categories, or levels of
        `within`). Default: all pairs, or all against `ref_group`.
    ref_group : str, optional
        Compare every other group with this one.
    within : str, optional
        Compare levels of this aesthetic (e.g. ``"fill"``) within each x
        category, for dodged plots, instead of comparing x categories.
    dodge_width : float, default=0.9
        Dodge width of the groups being compared, with `within`; 0.9
        matches the default of `geom_boxplot` and `position_dodge`.
    method : {"t-test", "student", "mann-whitney"}, default="t-test"
        Welch's t-test (R's ``t.test`` default), Student's t-test (equal
        variances), or the Mann-Whitney U test (R's ``wilcox.test`` for
        two samples). With ``paired=True``: paired t-test, or the Wilcoxon
        signed-rank test for "mann-whitney".
    paired : bool, default=False
        Pair observations by their order within each group.
    p_adjust : {"holm", "bh", "bonferroni"} or None, default="holm"
        Multiple-testing correction across the comparisons in a panel.
    label_type : {"stars", "p"}, default="stars"
        Stars (``ns``, ``*`` <= 0.05, ``**`` <= 0.01, ``***`` <= 0.001,
        ``****`` <= 0.0001) or the p-value. Uses adjusted p-values unless
        `p_adjust` is None. (Not ``label``: that is the text aesthetic.)
    hide_ns : bool, default=False
        Leave out brackets with p > 0.05.
    step : float, default=0.08
        Vertical distance between stacked brackets, as a fraction of the
        panel's data range.
    tip_length : float, default=0.02
        Length of the bracket ends, as a fraction of the data range.

    Notes
    -----
    Computed variables: ``p``, ``p_adj``, ``label``, ``xmin``, ``xmax``,
    ``y`` (bracket height), ``tip`` (bracket end length).
    """

    REQUIRED_AES = {"x", "y"}
    DEFAULT_PARAMS = {
        "geom": "bracket",
        "position": "identity",
        "na_rm": False,
        "comparisons": None,
        "ref_group": None,
        "within": None,
        "dodge_width": 0.9,
        "method": "t-test",
        "paired": False,
        "p_adjust": "holm",
        "label_type": "stars",
        "hide_ns": False,
        "step": 0.08,
        "tip_length": 0.02,
    }
    CREATES = {"p", "p_adj", "label", "xmin", "xmax", "tip", "ymin", "ymax"}
    DROPPED_AES = ["fill", "color", "colour", "alpha", "shape", "size", "group"]

    def __init__(self, mapping=None, data=None, **kwargs):
        method = kwargs.get("method", "t-test")
        if method not in TESTS:
            raise ValueError(f"method must be one of {TESTS}, got {method!r}")
        adj = kwargs.get("p_adjust", "holm")
        if adj is not None and adj not in ADJUSTMENTS:
            raise ValueError(f"p_adjust must be one of {ADJUSTMENTS} or None, got {adj!r}")
        if "label" in kwargs:
            raise TypeError(
                'use label_type="stars" or "p"; label is the text aesthetic'
            )
        if kwargs.get("label_type", "stars") not in ("stars", "p"):
            raise ValueError('label_type must be "stars" or "p"')
        super().__init__(mapping, data, **kwargs)

    def _pairs(self, names: list[str]) -> list[tuple[str, str]]:
        params = self.params
        if params["comparisons"] is not None:
            return [(str(a), str(b)) for a, b in params["comparisons"]]
        if params["ref_group"] is not None:
            ref = str(params["ref_group"])
            return [(ref, n) for n in names if n != ref]
        return list(combinations(names, 2))

    def _tests(self, data: pd.DataFrame, scales) -> pd.DataFrame:
        """One row per comparison: positions of both ends, p-value"""
        params = self.params
        within = params["within"]
        rows = []
        if within is None:
            levels = _x_levels(scales.x)
            present = sorted(data["x"].unique())
            names = (
                [levels[int(x) - 1] for x in present]
                if levels
                else [str(x) for x in present]
            )
            for a, b in self._pairs(names):
                xa, xb = _resolve(a, levels, "group"), _resolve(b, levels, "group")
                ya = data.loc[data["x"] == xa, "y"].to_numpy(float)
                yb = data.loc[data["x"] == xb, "y"].to_numpy(float)
                rows.append((xa, xb, ya, yb, (data["x"] >= min(xa, xb)) & (data["x"] <= max(xa, xb))))
        else:
            if within not in data:
                raise ValueError(
                    f"within={within!r} is not a mapped aesthetic of this layer; "
                    f"map it, e.g. aes({within}=...)"
                )
            width = params["dodge_width"]
            for x, at_x in data.groupby("x", sort=True):
                order = at_x.groupby(within, observed=True)["group"].min().sort_values()
                names = [str(n) for n in order.index]
                n = len(names)
                pos = {
                    name: x + (i - (n - 1) / 2) * width / n
                    for i, name in enumerate(names)
                }
                for a, b in self._pairs(names):
                    if a not in pos or b not in pos:
                        continue
                    ya = at_x.loc[at_x[within].astype(str) == a, "y"].to_numpy(float)
                    yb = at_x.loc[at_x[within].astype(str) == b, "y"].to_numpy(float)
                    rows.append((pos[a], pos[b], ya, yb, data["x"] == x))

        out = []
        for xa, xb, ya, yb, covered in rows:
            if len(ya) < 2 or len(yb) < 2:
                continue
            p = _test(ya, yb, params["method"], params["paired"])
            out.append(
                {
                    "xmin": min(xa, xb),
                    "xmax": max(xa, xb),
                    "p": p,
                    "local_max": float(data.loc[covered, "y"].max()),
                }
            )
        return pd.DataFrame(out, columns=["xmin", "xmax", "p", "local_max"])

    def compute_panel(self, data: pd.DataFrame, scales):
        params = self.params
        res = self._tests(data, scales)
        if not len(res):
            return pd.DataFrame(columns=["xmin", "xmax", "y", "label", "p", "p_adj", "PANEL"])

        res["p_adj"] = p_adjust(res["p"], params["p_adjust"])
        p_shown = res["p_adj"] if params["p_adjust"] else res["p"]
        prefix = "p.adj" if params["p_adjust"] and len(res) > 1 else "p"
        res["label"] = [format_p(p, params["label_type"], prefix) for p in p_shown]
        if params["hide_ns"]:
            res = res[p_shown <= 0.05].reset_index(drop=True)
            if not len(res):
                return pd.DataFrame(columns=["xmin", "xmax", "y", "label", "p", "p_adj", "PANEL"])

        ymin, ymax = float(data["y"].min()), float(data["y"].max())
        rng = (ymax - ymin) or 1.0
        step = params["step"] * rng
        tip = params["tip_length"] * rng

        # Narrow brackets first; each goes just above the data it spans
        # and above any placed bracket it overlaps
        res = res.assign(_span=res["xmax"] - res["xmin"]).sort_values(
            ["_span", "xmin"], kind="stable"
        )
        placed: list[tuple[float, float, float]] = []
        heights = []
        for xa, xb, local in zip(res["xmin"], res["xmax"], res["local_max"]):
            y = local + step
            for pa, pb, py in placed:
                if pa <= xb and xa <= pb:
                    y = max(y, py + step)
            placed.append((xa, xb, y))
            heights.append(y)
        res["y"] = heights
        res["tip"] = tip
        # Room for the label above the bracket when training the y scale
        res["ymin"] = res["y"] - tip
        res["ymax"] = res["y"] + 0.6 * step
        res["x"] = (res["xmin"] + res["xmax"]) / 2
        res["PANEL"] = data["PANEL"].iloc[0]
        res["group"] = np.arange(len(res))
        return res.drop(columns=["_span", "local_max"]).reset_index(drop=True)


class geom_bracket(geom):
    """
    Brackets with a label, e.g. for significance

    Use with `stat_compare_means`, or alone with your own table of
    comparisons (e.g. p-values from DESeq2 or limma).

    Parameters
    ----------
    mapping : aes
        Requires `xmin`, `xmax` (category names or positions), `y`
        (bracket height) and `label`. `tip` sets the length of the
        bracket ends in data units; by default 2% of the y range.
    size : float
        Line width of the bracket.
    fontsize : float, default=9
        Size of the label in points.
    label_gap : float, default=0.01
        Space between bracket and label, as a fraction of the y range.
    """

    DEFAULT_AES = {
        "alpha": 1,
        "color": "black",
        "linetype": "solid",
        "size": 0.4,
        "tip": None,
    }
    REQUIRED_AES = {"xmin", "xmax", "y", "label"}
    DEFAULT_PARAMS = {
        "stat": "identity",
        "position": "identity",
        "na_rm": False,
        "fontsize": 9,
        "label_gap": 0.01,
    }
    draw_legend = staticmethod(geom_path.draw_legend)

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
        yr = panel_params.y.range
        span = yr[1] - yr[0]
        tip = data["tip"].astype(float)
        tip = tip.where(tip.notna(), 0.02 * span)
        lines = [
            [(a, y - t), (a, y), (b, y), (b, y - t)]
            for a, b, y, t in zip(data["xmin"], data["xmax"], data["y"], tip)
        ]
        color = to_rgba(data["color"], data["alpha"])
        ax.add_collection(
            LineCollection(
                lines,
                colors=color,
                linewidths=data["size"] * SIZE_FACTOR,
                linestyles=list(data["linetype"]),
                zorder=self.params["zorder"],
                rasterized=self.params["raster"],
            )
        )
        gap = self.params["label_gap"] * span
        colors = color if not isinstance(color, tuple) else [color] * len(data)
        for a, b, y, lab, c in zip(
            data["xmin"], data["xmax"], data["y"], data["label"], colors
        ):
            ax.text(
                (a + b) / 2,
                y + gap,
                str(lab),
                ha="center",
                va="bottom",
                fontsize=self.params["fontsize"],
                color=c,
                zorder=self.params["zorder"],
                clip_on=False,
            )
