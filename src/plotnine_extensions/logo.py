"""
Sequence logos, in the spirit of R's ggseqlogo

Each letter is drawn as its glyph outline, stretched to fill a box whose
height is the letter's value. Positive values stack upwards with the
tallest on top; negative values (e.g. attribution scores) stack downwards
from zero with the largest magnitude at the bottom.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from plotnine._utils import to_rgba
from plotnine.geoms.geom import geom

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from matplotlib.axes import Axes
    from matplotlib.offsetbox import DrawingArea
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view
    from plotnine.layer import layer

__all__ = ["LOGO_PALETTES", "geom_logo", "logo_data"]

_DNA = {"A": "#109648", "C": "#255C99", "G": "#F7B32B", "T": "#D62839"}

LOGO_PALETTES: dict[str, dict[str, str]] = {
    "dna": _DNA,
    "rna": {**{k: v for k, v in _DNA.items() if k != "T"}, "U": _DNA["T"]},
    # Amino acids grouped by side-chain chemistry
    "protein": {
        **dict.fromkeys("GSTYC", "#109648"),  # polar
        **dict.fromkeys("QN", "#5E239D"),  # amide
        **dict.fromkeys("KRH", "#255C99"),  # basic
        **dict.fromkeys("DE", "#D62839"),  # acidic
        **dict.fromkeys("AVLIPWFM", "#1F1F1F"),  # hydrophobic
    },
}
"""Letter colours used when `fill` is not mapped"""

_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
_IGNORED = set("-.N*X")


def _auto_palette(letters) -> dict[str, str]:
    letters = {str(x).upper() for x in letters}
    for name in ("dna", "rna"):
        if letters <= set(LOGO_PALETTES[name]):
            return LOGO_PALETTES[name]
    return LOGO_PALETTES["protein"]


@lru_cache(maxsize=256)
def _glyph(letter: str, family: str | None, weight: str):
    """
    Outline of a letter, scaled to the unit square
    """
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath

    path = TextPath(
        (0, 0), letter, size=1, prop=FontProperties(family=family, weight=weight)
    )
    v = path.vertices.copy()
    lo, hi = v.min(axis=0), v.max(axis=0)
    span = np.where(hi - lo > 0, hi - lo, 1)
    return (v - lo) / span, path.codes


class geom_logo(geom):
    """
    Sequence logo

    Letters are stacked per position and stretched to their heights.
    Negative heights stack below zero, so attribution or in silico
    mutagenesis scores draw as they do in genomics model papers.

    Parameters
    ----------
    mapping : aes
        Requires `x` (position), `y` (letter height) and `label` (the
        letter). Map `fill` to colour letters by something other than
        their identity.
    data : DataFrame
        One row per position and letter; `logo_data` builds it from
        sequences or matrices.
    width : float, default=0.9
        Width of a letter as a fraction of the distance between
        positions.
    palette : str or dict, default="auto"
        Letter colours when `fill` is not mapped: ``"dna"``, ``"rna"``,
        ``"protein"`` (by side-chain chemistry), a ``{letter: colour}``
        dict, or ``"auto"`` to pick from the letters present.
    family : str, default=None
        Font family of the glyphs; `None` uses matplotlib's default sans.
    fontweight : str, default="bold"
        Font weight of the glyphs.
    """

    DEFAULT_AES = {"fill": None, "alpha": 1, "color": None, "size": 0.0}
    REQUIRED_AES = {"x", "y", "label"}
    DEFAULT_PARAMS = {
        "stat": "identity",
        "position": "identity",
        "na_rm": False,
        "width": 0.9,
        "palette": "auto",
        "family": None,
        "fontweight": "bold",
    }

    def setup_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data[np.isfinite(data["y"]) & (data["y"] != 0)].copy()
        data["label"] = data["label"].astype(str)
        width = self.params["width"]
        data["xmin"] = data["x"] - width / 2
        data["xmax"] = data["x"] + width / 2

        ymin = np.zeros(len(data))
        ymax = np.zeros(len(data))
        y = data["y"].to_numpy(float)
        keys = data[["PANEL", "x"]].astype(str).agg("|".join, axis=1).to_numpy()
        for key in pd.unique(keys):
            idx = np.flatnonzero(keys == key)
            pos = idx[y[idx] > 0]
            neg = idx[y[idx] < 0]
            # Tallest letter on top; for negatives, largest magnitude lowest
            pos = pos[np.argsort(y[pos], kind="stable")]
            neg = neg[np.argsort(-y[neg], kind="stable")]
            top = np.cumsum(y[pos])
            ymax[pos], ymin[pos] = top, top - y[pos]
            bottom = np.cumsum(y[neg])
            ymin[neg], ymax[neg] = bottom, bottom - y[neg]
        data["ymin"], data["ymax"] = ymin, ymax
        return data

    def draw_panel(
        self,
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
    ):
        from matplotlib.collections import PathCollection
        from matplotlib.path import Path

        if not len(data):
            return
        data = coord.transform(data, panel_params)
        params = self.params

        palette = params["palette"]
        if isinstance(palette, str):
            palette = (
                _auto_palette(data["label"])
                if palette == "auto"
                else LOGO_PALETTES[palette]
            )
        fill = [
            f if f is not None else palette.get(str(lab).upper(), "#7f7f7f")
            for f, lab in zip(data["fill"], data["label"])
        ]
        facecolors = to_rgba(fill, data["alpha"])

        paths = []
        for lab, x0, x1, y0, y1 in zip(
            data["label"], data["xmin"], data["xmax"], data["ymin"], data["ymax"]
        ):
            unit, codes = _glyph(lab, params["family"], params["fontweight"])
            verts = np.column_stack(
                [x0 + unit[:, 0] * (x1 - x0), y0 + unit[:, 1] * (y1 - y0)]
            )
            paths.append(Path(verts, codes))

        edge = data["color"]
        col = PathCollection(
            paths,
            facecolors=facecolors,
            edgecolors="none" if edge.isna().all() else list(edge),
            linewidths=data["size"],
            zorder=params["zorder"],
            rasterized=params["raster"],
        )
        ax.add_collection(col)

    @staticmethod
    def draw_legend(
        data: pd.Series[Any], da: DrawingArea, lyr: layer
    ) -> DrawingArea:
        from matplotlib.patches import Rectangle

        fill = data["fill"] if data["fill"] is not None else "#7f7f7f"
        da.add_artist(
            Rectangle(
                (0, 0),
                da.width,
                da.height,
                facecolor=to_rgba(fill, data["alpha"]),
                linewidth=0,
            )
        )
        return da


def _alphabet_of(sequences: Sequence[str]) -> str:
    letters = set("".join(sequences).upper()) - _IGNORED
    for alphabet in ("ACGT", "ACGU"):
        if letters <= set(alphabet):
            return alphabet
    return "".join(sorted(letters)) if not letters <= set(_AMINO_ACIDS) else _AMINO_ACIDS


def _counts(sequences: Sequence[str], alphabet: str) -> np.ndarray:
    seqs = [s.upper() for s in sequences]
    lengths = {len(s) for s in seqs}
    if len(lengths) != 1:
        raise ValueError(
            f"sequences must be aligned (equal length), got lengths {sorted(lengths)}"
        )
    arr = np.array([list(s) for s in seqs])
    return np.stack([(arr == a).sum(axis=0) for a in alphabet], axis=1).astype(float)


def logo_data(
    data,
    alphabet: str | Sequence[str] | None = None,
    method: str = "bits",
    sequence: str | None = None,
    start: int = 1,
    correction: bool = True,
) -> pd.DataFrame:
    """
    Long table of letter heights for `geom_logo`

    Parameters
    ----------
    data : list of str, array or DataFrame
        Aligned sequences of equal length; or a positions x letters matrix
        (numpy array, or a DataFrame whose columns are the letters) of
        counts, probabilities or scores.
    alphabet : str or sequence of str, optional
        Letters, in matrix column order. Inferred from sequences (DNA,
        RNA or protein) or from DataFrame columns; required for a numpy
        matrix.
    method : {"bits", "probability", "counts", "none"}
        ``"bits"``: information content, each letter's share of it.
        ``"probability"``: frequencies. ``"counts"``: raw counts.
        ``"none"``: use the matrix values as heights, e.g. attribution
        scores, which may be negative.
    sequence : str, optional
        With ``method="none"``, keep only the letter of this sequence at
        each position: the usual way to show contribution scores
        (hypothetical scores times the one-hot sequence).
    start : int, default=1
        Number of the first position.
    correction : bool, default=True
        For ``"bits"`` from sequences, subtract the approximate
        small-sample correction ``(s - 1) / (2 ln 2 n)`` of Schneider et
        al. (1986) from the information content, for alphabet size ``s``
        and ``n`` sequences.

    Returns
    -------
    pandas.DataFrame
        ``position``, ``letter``, ``height``.

    Examples
    --------
    ```python
    ggplot(logo_data(sites), aes("position", "height", label="letter"))
    + geom_logo()
    ```
    """
    methods = ("bits", "probability", "counts", "none")
    if method not in methods:
        raise ValueError(f"method must be one of {methods}, got {method!r}")

    n_seqs = None
    if isinstance(data, (list, tuple, pd.Series)) and len(data) and isinstance(
        next(iter(data)), str
    ):
        alphabet = alphabet or _alphabet_of(data)
        matrix = _counts(list(data), "".join(alphabet))
        n_seqs = len(data)
        if method == "none":
            raise ValueError('method="none" needs a matrix, not sequences')
    elif isinstance(data, pd.DataFrame):
        alphabet = alphabet or [str(c) for c in data.columns]
        matrix = data[list(data.columns)].to_numpy(float)
    else:
        matrix = np.asarray(data, float)
        if alphabet is None:
            raise ValueError("alphabet is required for a numpy matrix")

    letters = list(alphabet)
    if matrix.ndim != 2 or matrix.shape[1] != len(letters):
        raise ValueError(
            f"matrix must be positions x {len(letters)} letters, got {matrix.shape}"
        )

    if method == "none":
        heights = matrix.copy()
        if sequence is not None:
            if len(sequence) != len(matrix):
                raise ValueError(
                    f"sequence has length {len(sequence)}, matrix {len(matrix)}"
                )
            index = {a.upper(): i for i, a in enumerate(letters)}
            mask = np.zeros_like(heights, dtype=bool)
            for i, ch in enumerate(sequence.upper()):
                if ch in index:
                    mask[i, index[ch]] = True
            heights = np.where(mask, heights, 0.0)
    elif method == "counts":
        heights = matrix
    else:
        total = matrix.sum(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            prob = np.where(total > 0, matrix / total, 0.0)
        if method == "probability":
            heights = prob
        else:
            s = len(letters)
            with np.errstate(divide="ignore", invalid="ignore"):
                entropy = -np.nansum(np.where(prob > 0, prob * np.log2(prob), 0), axis=1)
            info = np.log2(s) - entropy
            if correction and n_seqs:
                info -= (s - 1) / (2 * np.log(2) * n_seqs)
            heights = prob * np.clip(info, 0, None)[:, None]

    positions = np.arange(start, start + len(matrix))
    out = pd.DataFrame(
        {
            "position": np.repeat(positions, len(letters)),
            "letter": np.tile(letters, len(matrix)),
            "height": heights.ravel(),
        }
    )
    return out
