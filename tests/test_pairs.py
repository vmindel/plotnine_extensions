import io
import warnings

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest
from plotnine import aes, geom_point, geom_smooth, stat_smooth, theme_bw
from scipy import stats

import plotnine_extensions as pnx


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    n = 90
    grp = np.repeat(["A", "B", "C"], 30)
    a = rng.normal(size=n) + np.repeat([0, 2, 4], 30)
    b = 0.8 * a + rng.normal(scale=0.6, size=n)
    c = rng.normal(size=n) * 20 + 100
    return pd.DataFrame({"a": a, "b": b, "c": c, "grp": grp})


def render(p, fmt="png"):
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p.save(buf, format=fmt, width=4, height=4, dpi=50, verbose=False)
    return buf.getbuffer().nbytes


def text_layers(p):
    return [
        lyr for lyr in p.layers if type(lyr.geom).__name__ == "geom_text"
    ]


@pytest.mark.parametrize("diag", ["density", "hist", "blank"])
@pytest.mark.parametrize("lower", ["points", "smooth", "cor", "blank"])
def test_renders(data, diag, lower):
    p = pnx.ggpairs(data, color="grp", diag=diag, lower=lower)
    assert render(p + theme_bw()) > 0


def test_renders_density2d_and_ungrouped(data):
    assert render(pnx.ggpairs(data, upper="density2d")) > 0
    assert render(pnx.ggpairs(data, diag="hist")) > 0


def test_default_columns_skip_color_and_text(data):
    df = data.assign(name=[f"r{i}" for i in range(len(data))])
    p = pnx.ggpairs(df, color="grp")
    assert list(p.data["xvar"].cat.categories) == ["a", "b", "c"]
    assert set(p.data.columns) >= {"grp", "name"}


def test_long_data_panels(data):
    p = pnx.ggpairs(data, upper="points")
    d = p.data
    # 3 variables: 3 lower and 3 upper panels of 90 rows
    assert len(d) == 6 * 90
    assert (d["part"] == "lower").sum() == 3 * 90
    lower = d[d["part"] == "lower"]
    names = list(d["xvar"].cat.categories)
    assert (
        lower["yvar"].map(names.index).astype(int)
        > lower["xvar"].map(names.index).astype(int)
    ).all()
    ab = d[(d["xvar"] == "a") & (d["yvar"] == "b")]
    np.testing.assert_allclose(ab["x"], data["a"])
    np.testing.assert_allclose(ab["y"], data["b"])


def test_cor_parts_add_no_rows(data):
    p = pnx.ggpairs(data)
    assert set(p.data["part"]) == {"lower"}
    p = pnx.ggpairs(data, lower="cor", upper="blank")
    assert len(p.data) == 0
    assert render(p) > 0


def test_correlation_text(data):
    p = pnx.ggpairs(data, color="grp", method="spearman", digits=3)
    overall, groups = [lyr._data for lyr in text_layers(p)]
    assert len(overall) == 3  # upper panels
    row = overall[(overall["xvar"] == "b") & (overall["yvar"] == "a")]
    r = stats.spearmanr(data["a"], data["b"])[0]
    assert row["label"].item().startswith(f"Corr: {r:.3f}")
    assert len(groups) == 9
    sub = data[data["grp"] == "B"]
    rb = stats.spearmanr(sub["a"], sub["b"])[0]
    g = groups[(groups["xvar"] == "b") & (groups["yvar"] == "a")
               & (groups["grp"] == "B")]
    assert g["label"].item().startswith(f"B: {rb:.3f}")


def test_stars_and_adjust(data):
    raw = text_layers(pnx.ggpairs(data))[0]._data
    assert raw["label"].str.endswith("***").any()
    plain = text_layers(pnx.ggpairs(data, stars=False))[0]._data
    assert not plain["label"].str.contains(r"\*").any()
    adj = text_layers(pnx.ggpairs(data, adjust="bonferroni"))[0]._data
    np.testing.assert_allclose(
        adj["p_adj"], np.minimum(raw["p"] * 3, 1)
    )


def test_text_inside_panel_ranges(data):
    t = text_layers(pnx.ggpairs(data, color="grp"))
    for d in (lyr._data for lyr in t):
        for _, row in d.iterrows():
            x, y = data[row["xvar"]], data[row["yvar"]]
            assert x.min() <= row["x"] <= x.max()
            assert y.min() < row["y"] < y.max()


def test_diag_rescaled_into_row_range(data):
    p = pnx.ggpairs(data, color="grp")
    ribbon = next(
        lyr._data for lyr in p.layers
        if type(lyr.geom).__name__ == "geom_ribbon"
    )
    for v in ("a", "b", "c"):
        d = ribbon[ribbon["yvar"] == v]
        lo, hi = data[v].min(), data[v].max()
        assert d["ymin"].eq(lo).all()
        assert d["ymax"].max() == pytest.approx(hi)
        assert (d["xvar"] == v).all()


def test_hist_stacks_to_counts(data):
    p = pnx.ggpairs(data, color="grp", diag="hist", bins=10)
    rects = next(
        lyr._data for lyr in p.layers
        if type(lyr.geom).__name__ == "geom_rect"
    )
    d = rects[rects["yvar"] == "a"]
    lo, hi = data["a"].min(), data["a"].max()
    counts = np.histogram(data["a"], bins=10)[0]
    top = d.groupby("xmin")["ymax"].max()
    np.testing.assert_allclose(
        (top.to_numpy() - lo) / (hi - lo), (counts / counts.max())[counts > 0]
    )


def test_custom_layers_go_to_their_triangle(data):
    p = pnx.ggpairs(
        data,
        lower=[geom_point(alpha=0.2), geom_smooth(method="lm")],
        upper=stat_smooth(method="lm"),
    )
    sub = [lyr._data for lyr in p.layers if callable(lyr._data)]
    assert len(sub) == 3
    assert set(sub[0](p.data)["part"]) == {"lower"}
    assert set(sub[2](p.data)["part"]) == {"upper"}
    assert render(p) > 0


def test_custom_layer_reused_is_not_mutated(data):
    pt = geom_point(alpha=0.5)
    pnx.ggpairs(data, lower=pt, upper=pt)
    assert pt.data is None


def test_missing_values_pairwise(data):
    df = data.copy()
    df.loc[:9, "c"] = np.nan
    p = pnx.ggpairs(df, upper="points")
    d = p.data
    ac = d[(d["xvar"] == "a") & (d["yvar"] == "c")]
    ab = d[(d["xvar"] == "a") & (d["yvar"] == "b")]
    assert len(ac) == 80 and len(ab) == 90
    assert render(p) > 0


def test_labels_and_numeric_color(data):
    df = data.assign(cl=np.repeat([0, 1, 2], 30))
    p = pnx.ggpairs(
        df, columns=["c", "a"], color="cl", labels={"a": "Signal A"}
    )
    assert list(p.data["xvar"].cat.categories) == ["c", "Signal A"]
    assert isinstance(p.data["cl"].dtype, pd.CategoricalDtype)
    assert render(p) > 0


def test_rasterise_points(data):
    p = pnx.ggpairs(data, color="grp", upper="points")
    assert render(pnx.rasterise(p, layers=["point"]), "pdf") < render(p, "pdf")


def test_errors(data):
    with pytest.raises(ValueError, match="not numeric"):
        pnx.ggpairs(data, columns=["a", "grp"])
    with pytest.raises(ValueError, match="at least 2"):
        pnx.ggpairs(data, columns=["a"])
    with pytest.raises(ValueError, match="not in data"):
        pnx.ggpairs(data, columns=["a", "zz"])
    with pytest.raises(ValueError, match="lower must be"):
        pnx.ggpairs(data, lower="hexbin")
    with pytest.raises(TypeError, match="upper must hold"):
        pnx.ggpairs(data, upper=[aes("a")])
    with pytest.raises(ValueError, match="diag"):
        pnx.ggpairs(data, diag="violin")
    with pytest.raises(ValueError, match="rename"):
        pnx.ggpairs(data.assign(part=1), columns=["a", "b"])
    with pytest.raises(ValueError, match="color column"):
        pnx.ggpairs(data, color="nope")
    with pytest.raises(ValueError, match="unique"):
        pnx.ggpairs(data, labels={"a": "b"})
