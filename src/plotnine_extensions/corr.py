"""
Correlation matrix heatmaps, in the spirit of R's ggcorrplot
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    coord_fixed,
    geom_point,
    geom_text,
    geom_tile,
    ggplot,
    ggtitle,
    scale_fill_gradient2,
    scale_size_area,
)
from plotnine.themes.elements import element_blank, element_text
from plotnine.themes.theme import theme
from plotnine.themes.theme_minimal import theme_minimal

from .signif import ADJUSTMENTS, p_adjust
from .themes import _rotated

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["cor_pmat", "ggcorrplot"]

CORR_METHODS = ("pearson", "spearman", "kendall")

# R's hclust names that differ in scipy. scipy's "ward" on a distance
# matrix is R's ward.D2; R's ward.D has no scipy equivalent.
_HC_ALIASES = {"ward.D2": "ward", "mcquitty": "weighted"}
_HC_METHODS = (
    "complete", "average", "single", "ward", "weighted", "centroid",
    "median",
)


def _as_frame(m, what: str) -> pd.DataFrame:
    if isinstance(m, pd.DataFrame):
        df = m.astype(float)
    else:
        a = np.asarray(m, float)
        if a.ndim != 2:
            raise ValueError(f"{what} must be 2-dimensional, got {a.ndim}")
        names = [f"V{i + 1}" for i in range(a.shape[1])]
        df = pd.DataFrame(a, index=names[: a.shape[0]], columns=names)
    if df.shape[0] != df.shape[1]:
        raise ValueError(f"{what} must be square, got shape {df.shape}")
    return df


def cor_pmat(
    x,
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
    adjust: Literal["holm", "bh", "bonferroni"] | None = None,
) -> pd.DataFrame:
    """
    p-values of the correlation between every pair of columns

    Each pair uses the rows where both columns are present, as R's
    `cor.test` does. The diagonal is 0.

    Parameters
    ----------
    x : DataFrame or array
        Observations in rows, variables in columns.
    method : {"pearson", "spearman", "kendall"}
        The test: `scipy.stats.pearsonr`, `spearmanr` or `kendalltau`.
    adjust : {"holm", "bh", "bonferroni"} or None
        Correct for multiple testing over the n(n - 1) / 2 distinct
        pairs. `None` (default, as in R) leaves the p-values raw.

    Returns
    -------
    DataFrame
        Symmetric, labelled with `x`'s column names.
    """
    from scipy import stats

    tests = {
        "pearson": stats.pearsonr,
        "spearman": stats.spearmanr,
        "kendall": stats.kendalltau,
    }
    if method not in tests:
        raise ValueError(f"method must be one of {CORR_METHODS}, got {method!r}")
    if adjust is not None and adjust not in ADJUSTMENTS:
        raise ValueError(
            f"adjust must be one of {ADJUSTMENTS} or None, got {adjust!r}"
        )
    if not isinstance(x, pd.DataFrame):
        a = np.asarray(x, float)
        x = pd.DataFrame(a, columns=[f"V{i + 1}" for i in range(a.shape[1])])
    a = x.to_numpy(float)
    n = a.shape[1]
    p = np.zeros((n, n))
    iu = np.triu_indices(n, 1)
    vals = np.empty(len(iu[0]))
    for k, (i, j) in enumerate(zip(*iu)):
        ok = ~(np.isnan(a[:, i]) | np.isnan(a[:, j]))
        if ok.sum() < 3:
            vals[k] = np.nan
            continue
        vals[k] = tests[method](a[ok, i], a[ok, j])[1]
    if adjust is not None:
        finite = ~np.isnan(vals)
        vals[finite] = p_adjust(vals[finite], adjust)
    p[iu] = vals
    p[(iu[1], iu[0])] = vals
    return pd.DataFrame(p, index=x.columns, columns=x.columns)


def _hc_order(corr: pd.DataFrame, method: str) -> list:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    method = _HC_ALIASES.get(method, method)
    if method not in _HC_METHODS:
        raise ValueError(
            f"hc_method must be one of {_HC_METHODS} or an R alias "
            f"{tuple(_HC_ALIASES)}, got {method!r}"
        )
    a = corr.to_numpy()
    if np.isnan(a).any():
        raise ValueError("hc_order=True needs a correlation matrix without NaN")
    d = (1 - a) / 2
    np.fill_diagonal(d, 0)
    d = np.clip((d + d.T) / 2, 0, 1)
    return list(corr.index[leaves_list(linkage(squareform(d), method))])


def _fmt(v: float, digits: int) -> str:
    # + 0.0 turns -0.00 into 0.00
    return f"{round(v, digits) + 0.0:.{digits}f}"


def ggcorrplot(
    corr,
    method: Literal["square", "circle"] = "square",
    type: Literal["full", "lower", "upper"] = "full",
    ggtheme=theme_minimal,
    title: str = "",
    show_legend: bool = True,
    legend_title: str = "Corr",
    show_diag: bool | None = None,
    colors: Sequence[str] = ("blue", "white", "red"),
    outline_color: str = "gray",
    hc_order: bool = False,
    hc_method: str = "complete",
    lab: bool = False,
    lab_col: str = "black",
    lab_size: float = 11,
    p_mat=None,
    sig_level: float = 0.05,
    insig: Literal["pch", "blank"] = "pch",
    pch: str = "x",
    pch_col: str = "black",
    pch_cex: float = 5,
    tl_cex: float = 12,
    tl_col: str = "black",
    tl_srt: float = 45,
    digits: int = 2,
) -> ggplot:
    """
    Heatmap of a correlation matrix

    Returns an ordinary `ggplot`, so layers, scales and themes can be
    added with `+`. Its data has one row per drawn cell, with columns
    `var1` (x), `var2` (y), `value`, and `pvalue` when `p_mat` is given.

    Parameters
    ----------
    corr : DataFrame or array
        A square correlation matrix, e.g. `df.corr()`. Values must lie
        in [-1, 1]; raw data raises an error instead of plotting.
    method : {"square", "circle"}
        Tiles, or circles whose area is proportional to |r|.
    type : {"full", "lower", "upper"}
        Which triangle to draw.
    ggtheme : theme class or instance
        Base theme, `theme_minimal` by default.
    title : str
    show_legend : bool
    legend_title : str
    show_diag : bool, optional
        Draw the diagonal. By default only for `type="full"`.
    colors : (low, mid, high)
        Colours for -1, 0 and 1.
    outline_color : str
        Tile border, or circle outline.
    hc_order : bool
        Order variables by hierarchical clustering on (1 - r) / 2.
    hc_method : str
        Linkage: `"complete"`, `"average"`, `"single"`, `"ward"` (R's
        `"ward.D2"` also accepted), `"weighted"` (R's `"mcquitty"`),
        `"centroid"`, `"median"`.
    lab : bool
        Print the coefficient in each cell.
    lab_col : str
    lab_size : float
        Points. R's `lab_size = 4` (mm) is about 11 here.
    p_mat : DataFrame or array, optional
        p-values with the same layout as `corr`, e.g. from `cor_pmat`.
        A DataFrame is aligned to `corr` by labels.
    sig_level : float
        Cells with p above this are insignificant.
    insig : {"pch", "blank"}
        Mark insignificant cells with `pch`, or leave them empty.
    pch : str
        matplotlib marker for insignificant cells; `"x"` is R's `pch = 4`.
    pch_col : str
    pch_cex : float
        Marker size, as `geom_point`'s `size`.
    tl_cex : float
        Tick label size in points.
    tl_col : str
        Tick label colour.
    tl_srt : float
        Rotation of the x tick labels in degrees.
    digits : int
        Decimals of the cell labels.
    """
    if method not in ("square", "circle"):
        raise ValueError(f'method must be "square" or "circle", got {method!r}')
    if type not in ("full", "lower", "upper"):
        raise ValueError(
            f'type must be "full", "lower" or "upper", got {type!r}'
        )
    if insig not in ("pch", "blank"):
        raise ValueError(f'insig must be "pch" or "blank", got {insig!r}')
    if len(colors) != 3:
        raise ValueError("colors must be (low, mid, high)")

    corr = _as_frame(corr, "corr")
    vals = corr.to_numpy()
    if np.nanmax(np.abs(vals), initial=0) > 1 + 1e-8:
        raise ValueError(
            "corr has values outside [-1, 1]; pass a correlation matrix "
            "such as df.corr(), not the data"
        )
    if list(corr.index) != list(corr.columns):
        raise ValueError("corr must have the same labels on rows and columns")
    if p_mat is not None:
        if isinstance(p_mat, pd.DataFrame):
            p_mat = p_mat.astype(float).reindex(
                index=corr.index, columns=corr.columns
            )
            if p_mat.isna().all(axis=None):
                raise ValueError("p_mat shares no labels with corr")
        else:
            a = np.asarray(p_mat, float)
            if a.shape != corr.shape:
                raise ValueError(
                    f"p_mat has shape {a.shape}, corr has {corr.shape}"
                )
            p_mat = pd.DataFrame(a, index=corr.index, columns=corr.columns)

    if hc_order:
        order = _hc_order(corr, hc_method)
        corr = corr.loc[order, order]
        if p_mat is not None:
            p_mat = p_mat.loc[order, order]
    if show_diag is None:
        show_diag = type == "full"

    names = list(corr.index)
    n = len(names)
    i, j = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    keep = np.ones((n, n), bool)
    if type == "lower":
        keep = i >= j
    elif type == "upper":
        keep = i <= j
    if not show_diag:
        keep &= i != j
    i, j = i[keep], j[keep]
    df = pd.DataFrame(
        {
            "var1": pd.Categorical.from_codes(i, names),
            "var2": pd.Categorical.from_codes(j, names),
            "value": corr.to_numpy()[i, j],
        }
    )
    df["abs_corr"] = df["value"].abs()

    ns = np.zeros(len(df), bool)
    if p_mat is not None:
        df["pvalue"] = p_mat.to_numpy()[i, j]
        ns = (df["pvalue"] > sig_level).to_numpy()
    shown = df[~ns] if insig == "blank" else df

    p = ggplot(df, aes("var1", "var2"))
    if method == "square":
        p += geom_tile(aes(fill="value"), data=shown, color=outline_color)
    else:
        # Area is proportional to |r| and r = 0 draws nothing, so sizes
        # compare across figures. ggcorrplot rescales to the data range.
        p += geom_point(
            aes(fill="value", size="abs_corr"),
            data=shown,
            shape="o",
            color=outline_color,
        )
        p += scale_size_area(max_size=10, limits=(0, 1), guide=None)
    low, mid, high = colors
    p += scale_fill_gradient2(
        low=low, mid=mid, high=high, midpoint=0, limits=(-1, 1),
        name=legend_title,
    )
    if lab:
        labels = shown[shown["value"].notna()].assign(
            label=lambda d: [_fmt(v, digits) for v in d["value"]]
        )
        p += geom_text(
            aes(label="label"), data=labels, color=lab_col, size=lab_size
        )
    if p_mat is not None and insig == "pch" and ns.any():
        p += geom_point(
            data=df[ns], shape=pch, color=pch_col, size=pch_cex
        )

    p += coord_fixed()
    p += ggtheme() if inspect.isclass(ggtheme) else ggtheme
    x_text = {}
    if tl_srt:
        r = _rotated(tl_srt, None, None).properties
        x_text = {k: r[k] for k in ("rotation", "ha", "va")}
    p += theme(
        axis_title=element_blank(),
        axis_text_x=element_text(size=tl_cex, color=tl_col, **x_text),
        axis_text_y=element_text(size=tl_cex, color=tl_col),
    )
    if not show_legend:
        p += theme(legend_position="none")
    if title:
        p += ggtitle(title)
    return p
