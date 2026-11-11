import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest
from plotnine import theme_bw
from scipy import stats

import plotnine_extensions as pnx


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(80, 6))
    x[:, 1] += x[:, 0]
    x[:, 2] -= x[:, 0]
    x[:, 4] += x[:, 3]
    return pd.DataFrame(x, columns=list("abcdef"))


def cells(p):
    return p.data


def layer_data(p, k):
    return p.layers[k].geom.data


@pytest.mark.parametrize("method", ["square", "circle"])
@pytest.mark.parametrize("kind", ["full", "lower", "upper"])
def test_renders(data, method, kind, tmp_path):
    p = pnx.ggcorrplot(
        data.corr(), method=method, type=kind, lab=True,
        p_mat=pnx.cor_pmat(data), title="t",
    )
    p.save(tmp_path / "p.png", width=4, height=4, dpi=50, verbose=False)
    assert (tmp_path / "p.png").stat().st_size > 0


@pytest.mark.parametrize(
    "kind, diag, n",
    [
        ("full", None, 36),
        ("full", False, 30),
        ("lower", None, 15),
        ("upper", None, 15),
        ("lower", True, 21),
    ],
)
def test_cell_counts(data, kind, diag, n):
    p = pnx.ggcorrplot(data.corr(), type=kind, show_diag=diag)
    assert len(cells(p)) == n


def test_triangles(data):
    lower = cells(pnx.ggcorrplot(data.corr(), type="lower"))
    upper = cells(pnx.ggcorrplot(data.corr(), type="upper"))
    assert (lower["var1"].cat.codes > lower["var2"].cat.codes).all()
    assert (upper["var1"].cat.codes < upper["var2"].cat.codes).all()


def test_values_match_matrix(data):
    c = data.corr()
    df = cells(pnx.ggcorrplot(c))
    for _, row in df.iterrows():
        assert row["value"] == pytest.approx(c.loc[row["var1"], row["var2"]])


def test_rejects_raw_data_and_bad_shapes(data):
    with pytest.raises(ValueError, match="correlation matrix"):
        pnx.ggcorrplot(data.iloc[:6] * 10)
    with pytest.raises(ValueError, match="square"):
        pnx.ggcorrplot(data.corr().iloc[:, :4])
    with pytest.raises(ValueError, match="p_mat has shape"):
        pnx.ggcorrplot(data.corr(), p_mat=np.zeros((3, 3)))
    with pytest.raises(ValueError, match="method"):
        pnx.ggcorrplot(data.corr(), method="ellipse")


def test_array_input():
    c = np.array([[1, 0.3], [0.3, 1]])
    df = cells(pnx.ggcorrplot(c))
    assert list(df["var1"].cat.categories) == ["V1", "V2"]


def test_hc_order_groups_correlated(data):
    df = cells(pnx.ggcorrplot(data.corr(), hc_order=True))
    order = list(df["var1"].cat.categories)
    assert abs(order.index("a") - order.index("b")) == 1
    assert abs(order.index("d") - order.index("e")) == 1


def test_hc_method_aliases(data):
    pnx.ggcorrplot(data.corr(), hc_order=True, hc_method="ward.D2")
    with pytest.raises(ValueError, match="hc_method"):
        pnx.ggcorrplot(data.corr(), hc_order=True, hc_method="ward.D")


def test_hc_order_reorders_pvalues(data):
    pm = pnx.cor_pmat(data)
    df = cells(pnx.ggcorrplot(data.corr(), hc_order=True, p_mat=pm))
    for _, row in df.iterrows():
        assert row["pvalue"] == pytest.approx(pm.loc[row["var1"], row["var2"]])


def test_p_mat_aligned_by_label(data):
    pm = pnx.cor_pmat(data)
    shuffled = pm.loc[::-1, ::-1]
    a = cells(pnx.ggcorrplot(data.corr(), p_mat=pm))
    b = cells(pnx.ggcorrplot(data.corr(), p_mat=shuffled))
    np.testing.assert_allclose(a["pvalue"], b["pvalue"])


def test_insig_pch_and_blank(data):
    c, pm = data.corr(), pnx.cor_pmat(data)
    n_ns = int(((pm > 0.05).to_numpy()).sum())
    assert n_ns > 0
    pch = pnx.ggcorrplot(c, p_mat=pm, lab=True)
    assert len(layer_data(pch, 0)) == 36
    assert len(layer_data(pch, -1)) == n_ns
    blank = pnx.ggcorrplot(c, p_mat=pm, lab=True, insig="blank")
    assert len(layer_data(blank, 0)) == 36 - n_ns
    assert len(layer_data(blank, 1)) == 36 - n_ns  # labels
    assert len(blank.layers) == 2


def test_labels(data):
    c = pd.DataFrame([[1, -0.001], [-0.001, 1]], index=list("xy"),
                     columns=list("xy"))
    p = pnx.ggcorrplot(c, lab=True, digits=2)
    assert set(layer_data(p, 1)["label"]) == {"1.00", "0.00"}


def test_theme_and_legend(data):
    pnx.ggcorrplot(data.corr(), ggtheme=theme_bw()).draw()
    fig = pnx.ggcorrplot(data.corr(), show_legend=False).draw()
    assert not fig.legends and all(not ax.get_legend() for ax in fig.axes)


def test_cor_pmat_matches_scipy(data):
    pm = pnx.cor_pmat(data)
    assert np.allclose(pm, pm.T)
    assert (np.diag(pm) == 0).all()
    assert pm.loc["a", "c"] == pytest.approx(
        stats.pearsonr(data["a"], data["c"])[1]
    )
    sp = pnx.cor_pmat(data, method="spearman")
    assert sp.loc["d", "f"] == pytest.approx(
        stats.spearmanr(data["d"], data["f"])[1]
    )


def test_cor_pmat_pairwise_complete(data):
    d = data.copy()
    d.loc[:9, "a"] = np.nan
    pm = pnx.cor_pmat(d)
    ok = d["a"].notna()
    assert pm.loc["a", "b"] == pytest.approx(
        stats.pearsonr(d.loc[ok, "a"], d.loc[ok, "b"])[1]
    )


def test_cor_pmat_adjust(data):
    raw = pnx.cor_pmat(data)
    holm = pnx.cor_pmat(data, adjust="holm")
    iu = np.triu_indices(6, 1)
    np.testing.assert_allclose(
        holm.to_numpy()[iu], pnx.p_adjust(raw.to_numpy()[iu], "holm")
    )
    with pytest.raises(ValueError, match="adjust"):
        pnx.cor_pmat(data, adjust="fdr")
