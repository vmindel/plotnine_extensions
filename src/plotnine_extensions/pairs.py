"""
Scatterplot matrices, in the spirit of R's GGally::ggpairs
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    facet_grid,
    geom_blank,
    geom_density_2d,
    geom_line,
    geom_point,
    geom_rect,
    geom_ribbon,
    geom_smooth,
    geom_text,
    ggplot,
    labs,
)
from plotnine.layer import layer as _layer

from .corr import CORR_METHODS
from .signif import ADJUSTMENTS, p_adjust

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ["ggpairs"]

PANELS = ("points", "smooth", "density2d", "cor", "blank")
DIAGS = ("density", "hist", "blank")
# Columns of the long data; a carried column with one of these names
# would be overwritten
RESERVED = ("x", "y", "xvar", "yvar", "part")
# GGally's signif_stars thresholds
_STARS = ((1e-3, "***"), (1e-2, "**"), (0.05, "*"), (0.1, "."))


def _stars(p: float) -> str:
    if not np.isfinite(p):
        return ""
    for cut, s in _STARS:
        if p < cut:
            return s
    return ""


def _cor_test(x: np.ndarray, y: np.ndarray, method: str):
    from scipy import stats

    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan, np.nan
    test = {
        "pearson": stats.pearsonr,
        "spearman": stats.spearmanr,
        "kendall": stats.kendalltau,
    }[method]
    res = test(x, y)
    return float(res[0]), float(res[1])


def _bw_nrd0(x: np.ndarray) -> float:
    """R's default density bandwidth, bw.nrd0"""
    sd = np.std(x, ddof=1)
    q75, q25 = np.percentile(x, [75, 25])
    lo = min(sd, (q75 - q25) / 1.34)
    if lo <= 0:
        lo = sd or abs(x[0]) or 1.0
    return 0.9 * lo * len(x) ** -0.2


def _density(x: np.ndarray, grid: np.ndarray) -> np.ndarray | None:
    from scipy.stats import gaussian_kde

    x = x[np.isfinite(x)]
    if len(x) < 2 or np.ptp(x) == 0:
        return None
    sd = np.std(x, ddof=1)
    return gaussian_kde(x, bw_method=_bw_nrd0(x) / sd)(grid)


def _fmt(v: float, digits: int) -> str:
    if not np.isfinite(v):
        return "NA"
    return f"{round(v, digits) + 0.0:.{digits}f}"


def _as_layers(spec, part: str, what: str) -> list:
    """Layers for one triangle, from a panel name or plotnine objects"""
    if isinstance(spec, str):
        if spec not in PANELS:
            raise ValueError(
                f"{what} must be one of {PANELS} or plotnine layers, "
                f"got {spec!r}"
            )
        if spec == "points":
            spec = [geom_point(size=1)]
        elif spec == "smooth":
            spec = [geom_point(size=1), geom_smooth(method="lm")]
        elif spec == "density2d":
            spec = [geom_density_2d()]
        else:
            return []
    if not isinstance(spec, (list, tuple)):
        spec = [spec]

    def subset(d, part=part):
        return d[d["part"] == part]

    out = []
    for obj in spec:
        if isinstance(obj, (list, tuple)):
            out.extend(_as_layers(list(obj), part, what))
            continue
        obj = deepcopy(obj)
        if isinstance(obj, _layer):
            lyr = obj
        elif hasattr(obj, "to_layer"):
            lyr = obj.to_layer()
        else:
            raise TypeError(
                f"{what} must hold geoms, stats or layers, got "
                f"{type(obj).__name__}"
            )
        # A layer with its own data is the caller's business
        if lyr._data is None:
            lyr._data = subset
        out.append(lyr)
    return out


def ggpairs(
    data: pd.DataFrame,
    columns: Sequence[str] | None = None,
    color: str | None = None,
    *,
    lower="points",
    diag: Literal["density", "hist", "blank"] = "density",
    upper="cor",
    labels: Mapping[str, str] | None = None,
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
    stars: bool = True,
    adjust: Literal["holm", "bh", "bonferroni"] | None = None,
    digits: int = 2,
    cor_size: float = 9,
    bins: int = 30,
    alpha: float = 0.4,
    title: str | None = None,
) -> ggplot:
    """
    Scatterplot matrix of the columns of a data frame

    Every pair of `columns` gets a panel: scatter plots below the
    diagonal, each variable's distribution on it, and correlation
    coefficients above it, by default. The result is one ordinary
    `ggplot` faceted with `facet_grid("yvar ~ xvar", scales="free")`, so
    themes, scales and further layers add on with `+`. Each column of
    panels shares the x axis of its variable and each row the y axis
    of its variable; the diagonal densities and histograms are rescaled
    into the row's y range, so every y axis reads in that variable's
    units.

    The plot's data is the long form of the pairs drawn from raw
    values (parts that are `"cor"` or `"blank"` add no rows): one row
    per observation and panel, with columns `x`, `y`, `xvar`, `yvar`,
    `part` (`"lower"` or `"upper"`) and every column of `data` that is
    not in `columns`. The plot maps `x`, `y` and, when given, `color`.
    A layer added afterwards draws in both triangles; restrict it with
    `data=lambda d: d[d.part == "lower"]`.

    Parameters
    ----------
    data : DataFrame
    columns : sequence of str, optional
        Variables to pair, in order (first at the top left). By default
        every numeric column except `color`. They must be numeric;
        pass a grouping column as `color` instead.
    color : str, optional
        A grouping column. It is treated as categorical (a numeric one
        is converted), colours points, lines and text, fills densities
        and histograms, and splits the correlations by group. Change
        the colours with
        `scale_color_manual(..., aesthetics=["color", "fill"])`.
    lower, upper : str or plotnine layers
        What to draw below and above the diagonal: `"points"`,
        `"smooth"` (points and a linear fit with its confidence band),
        `"density2d"` (contours), `"cor"` (coefficients) or `"blank"`;
        or a geom, stat, layer, or list of these, e.g.
        `[geom_point(alpha=0.2), geom_smooth(method="loess")]`. Given
        layers draw only in their triangle (unless they bring their own
        `data`) and inherit the `x`, `y` and `color` mappings.
    diag : {"density", "hist", "blank"}
        Kernel density (R's default bandwidth, `bw.nrd0`) or a stacked
        histogram of each variable. With `color`, densities are per
        group, each integrating to one.
    labels : mapping, optional
        Display names for the strips, `{column: label}`; unlisted
        columns keep their names. `xvar` and `yvar` hold these labels.
    method : {"pearson", "spearman", "kendall"}
        Correlation coefficient and its test, from `scipy.stats`.
        Each pair uses the rows where both values are present.
    stars : bool
        Append GGally's significance stars: `***` p < 0.001, `**`
        < 0.01, `*` < 0.05, `.` < 0.1.
    adjust : {"holm", "bh", "bonferroni"} or None
        Correct the p-values behind the stars for multiple testing,
        over every coefficient drawn (each pair, and each group within
        it). `None` (default, as in GGally) leaves them raw.
    digits : int
        Decimals of the coefficients.
    cor_size : float
        Size of the coefficient text in points.
    bins : int
        Number of histogram bins, shared by all groups.
    alpha : float
        Opacity of the density and histogram fills.
    title : str, optional

    Returns
    -------
    ggplot
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"data must be a DataFrame, got {type(data).__name__}")
    if diag not in DIAGS:
        raise ValueError(f"diag must be one of {DIAGS}, got {diag!r}")
    if method not in CORR_METHODS:
        raise ValueError(
            f"method must be one of {CORR_METHODS}, got {method!r}"
        )
    if adjust is not None and adjust not in ADJUSTMENTS:
        raise ValueError(
            f"adjust must be one of {ADJUSTMENTS} or None, got {adjust!r}"
        )
    if color is not None and color not in data.columns:
        raise ValueError(f"color column {color!r} is not in data")

    if columns is None:
        columns = [
            c
            for c in data.columns
            if c != color and pd.api.types.is_numeric_dtype(data[c])
            and not pd.api.types.is_bool_dtype(data[c])
        ]
    columns = list(columns)
    missing = [c for c in columns if c not in data.columns]
    if missing:
        raise ValueError(f"columns not in data: {missing}")
    if len(set(columns)) != len(columns):
        raise ValueError("columns has duplicates")
    if len(columns) < 2:
        raise ValueError(f"need at least 2 columns to pair, got {columns}")
    if color in columns:
        raise ValueError(f"{color!r} is both in columns and the color column")
    for c in columns:
        if not pd.api.types.is_numeric_dtype(data[c]) or (
            pd.api.types.is_bool_dtype(data[c])
        ):
            raise ValueError(
                f"column {c!r} is not numeric; pass a grouping column as "
                "color= instead"
            )

    labels = dict(labels or {})
    names = [str(labels.get(c, c)) for c in columns]
    if len(set(names)) != len(names):
        raise ValueError(f"labels are not unique: {names}")
    carry = [c for c in data.columns if c not in columns]
    clash = sorted(set(carry) & set(RESERVED))
    if clash:
        raise ValueError(
            f"data has columns {clash}, which ggpairs uses in its long "
            "data; rename them"
        )

    df = data.reset_index(drop=True)
    groups = None
    if color is not None:
        g = df[color]
        if not isinstance(g.dtype, pd.CategoricalDtype):
            g = pd.Categorical(g)
        df = df.assign(**{color: g})
        groups = df[color].cat.categories

    vals = {c: df[c].to_numpy(float) for c in columns}
    rng = {}
    for c in columns:
        v = vals[c][np.isfinite(vals[c])]
        if len(v) == 0:
            raise ValueError(f"column {c!r} has no finite values")
        lo, hi = float(v.min()), float(v.max())
        if lo == hi:
            lo, hi = lo - 0.5, hi + 0.5
        rng[c] = (lo, hi)

    n = len(columns)
    xcat = pd.CategoricalDtype(names, ordered=False)

    def panel_cols(i, j, k):
        return {
            "xvar": pd.Categorical([names[j]] * k, dtype=xcat),
            "yvar": pd.Categorical([names[i]] * k, dtype=xcat),
        }

    parts = {"lower": lower, "upper": upper}
    raw_parts = [
        part
        for part, spec in parts.items()
        if not (isinstance(spec, str) and spec in ("cor", "blank"))
    ]

    # Long data of the panels drawn from raw values
    frames = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            part = "lower" if i > j else "upper"
            if part not in raw_parts:
                continue
            x, y = vals[columns[j]], vals[columns[i]]
            ok = np.isfinite(x) & np.isfinite(y)
            f = df.loc[ok, carry].assign(x=x[ok], y=y[ok], part=part)
            frames.append(f.assign(**panel_cols(i, j, int(ok.sum()))))
    if frames:
        long = pd.concat(frames, ignore_index=True)
    else:
        long = df.loc[[], carry].assign(
            x=[], y=[], part=[], **panel_cols(0, 0, 0)
        )

    # Every panel spans its variables' ranges, whatever it draws
    corners = []
    for i in range(n):
        for j in range(n):
            (xlo, xhi), (ylo, yhi) = rng[columns[j]], rng[columns[i]]
            corners.append(
                pd.DataFrame(
                    {"x": [xlo, xhi], "y": [ylo, yhi], **panel_cols(i, j, 2)}
                )
            )
    corners = pd.concat(corners, ignore_index=True)

    mapping = aes("x", "y")
    if color is not None:
        mapping = aes("x", "y", color=color)
    p = ggplot(long, mapping) + geom_blank(
        aes("x", "y"), data=corners, inherit_aes=False
    )

    # Diagonal
    if diag != "blank":
        p += _diag_layers(
            diag, df, columns, vals, rng, color, groups, panel_cols,
            bins, alpha,
        )

    # Triangles
    for part, spec in parts.items():
        if isinstance(spec, str) and spec == "cor":
            p += _cor_layers(
                part, df, columns, vals, rng, color, groups, panel_cols,
                method, stars, adjust, digits, cor_size,
            )
        else:
            for lyr in _as_layers(spec, part, part):
                p += lyr

    p += facet_grid("yvar ~ xvar", scales="free")
    p += labs(x="", y="")
    if title:
        p += labs(title=title)
    return p


def _diag_layers(
    diag, df, columns, vals, rng, color, groups, panel_cols, bins, alpha
):
    rows = []
    for i, c in enumerate(columns):
        lo, hi = rng[c]
        x = vals[c]
        if groups is None:
            sets = [(None, np.isfinite(x))]
        else:
            g = df[color]
            sets = [(lev, (g == lev).to_numpy()) for lev in groups]
        if diag == "density":
            grid = np.linspace(lo, hi, 512)
            dens = [(lev, _density(x[m], grid)) for lev, m in sets]
            dens = [(lev, d) for lev, d in dens if d is not None]
            if not dens:
                continue
            top = max(d.max() for _, d in dens)
            for lev, d in dens:
                f = pd.DataFrame(
                    {
                        "x": grid,
                        "ymin": lo,
                        "ymax": lo + d / top * (hi - lo),
                        **panel_cols(i, i, len(grid)),
                    }
                )
                if groups is not None:
                    f[color] = pd.Categorical([lev] * len(f), groups)
                rows.append(f)
        else:
            finite = x[np.isfinite(x)]
            edges = np.histogram_bin_edges(finite, bins=bins, range=(lo, hi))
            counts = [
                np.histogram(x[m & np.isfinite(x)], bins=edges)[0]
                for _, m in sets
            ]
            total = np.sum(counts, axis=0)
            top = total.max() or 1
            base = np.zeros(len(edges) - 1)
            for (lev, _), cnt in zip(sets, counts):
                f = pd.DataFrame(
                    {
                        "xmin": edges[:-1],
                        "xmax": edges[1:],
                        "ymin": lo + base / top * (hi - lo),
                        "ymax": lo + (base + cnt) / top * (hi - lo),
                        **panel_cols(i, i, len(cnt)),
                    }
                )
                base = base + cnt
                f = f[cnt > 0]
                if groups is not None:
                    f[color] = pd.Categorical([lev] * len(f), groups)
                rows.append(f)
    if not rows:
        return []
    d = pd.concat(rows, ignore_index=True)

    if diag == "density":
        if groups is None:
            return [
                geom_ribbon(
                    aes("x", ymin="ymin", ymax="ymax"), data=d,
                    inherit_aes=False, fill="grey", alpha=alpha,
                ),
                geom_line(
                    aes("x", "ymax"), data=d, inherit_aes=False
                ),
            ]
        return [
            geom_ribbon(
                aes("x", ymin="ymin", ymax="ymax", fill=color), data=d,
                inherit_aes=False, alpha=alpha,
            ),
            geom_line(
                aes("x", "ymax", color=color), data=d, inherit_aes=False
            ),
        ]
    fill = {} if groups is None else {"fill": color}
    return [
        geom_rect(
            aes(xmin="xmin", xmax="xmax", ymin="ymin", ymax="ymax", **fill),
            data=d, inherit_aes=False, color="white", size=0.2,
            alpha=alpha if groups is not None else 1,
            **({} if groups is not None else {"fill": "grey"}),
        )
    ]


def _cor_layers(
    part, df, columns, vals, rng, color, groups, panel_cols, method,
    stars, adjust, digits, cor_size,
):
    lines = []
    n = len(columns)
    for i in range(n):
        for j in range(n):
            if (part == "lower") != (i > j) or i == j:
                continue
            x, y = vals[columns[j]], vals[columns[i]]
            entries = [("Corr", None, *_cor_test(x, y, method))]
            if groups is not None:
                g = df[color]
                for lev in groups:
                    m = (g == lev).to_numpy()
                    entries.append(
                        (str(lev), lev, *_cor_test(x[m], y[m], method))
                    )
            (xlo, xhi), (ylo, yhi) = rng[columns[j]], rng[columns[i]]
            k = len(entries)
            for pos, (name, lev, r, pv) in enumerate(entries):
                lines.append(
                    {
                        "i": i, "j": j, "name": name, "lev": lev,
                        "r": r, "p": pv,
                        "x": (xlo + xhi) / 2,
                        "y": yhi - (pos + 1) * (yhi - ylo) / (k + 1),
                    }
                )
    if not lines:
        return []
    t = pd.DataFrame(lines)
    pvals = t["p"].to_numpy(float)
    if adjust is not None:
        ok = np.isfinite(pvals)
        pvals = pvals.copy()
        pvals[ok] = p_adjust(pvals[ok], adjust)
    t["p_adj"] = pvals
    t["label"] = [
        f"{name}: {_fmt(r, digits)}" + (_stars(pv) if stars else "")
        for name, r, pv in zip(t["name"], t["r"], pvals)
    ]
    xcat = panel_cols(0, 0, 0)["xvar"].dtype
    names = list(xcat.categories)
    t["xvar"] = pd.Categorical([names[j] for j in t["j"]], dtype=xcat)
    t["yvar"] = pd.Categorical([names[i] for i in t["i"]], dtype=xcat)

    overall = t[t["lev"].isna()]
    out = [
        geom_text(
            aes("x", "y", label="label"), data=overall, inherit_aes=False,
            size=cor_size, color="black",
        )
    ]
    if groups is not None:
        grp = t[t["lev"].notna()].copy()
        grp[color] = pd.Categorical(grp["lev"], groups)
        out.append(
            geom_text(
                aes("x", "y", label="label", color=color), data=grp,
                inherit_aes=False, size=cor_size, show_legend=False,
            )
        )
    return out
