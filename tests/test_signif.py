from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from plotnine import aes, facet_wrap, geom_boxplot, ggplot
from scipy import stats
from statsmodels.stats.multitest import multipletests

from plotnine_extensions import (
    format_p,
    geom_bracket,
    p_adjust,
    stat_compare_means,
)

LEVELS = ["WT", "KO", "Rescue", "Dbl"]


@pytest.fixture
def df():
    rng = np.random.default_rng(4)
    d = pd.concat(
        [
            pd.DataFrame({"cond": c, "y": rng.normal(m, 1, 30)})
            for c, m in zip(LEVELS, [0, 1.2, 0.3, 2])
        ],
        ignore_index=True,
    )
    d["cond"] = pd.Categorical(d["cond"], LEVELS)
    return d


def compute(df, **params):
    """Run the stat's panel computation on data as plotnine passes it."""
    s = stat_compare_means(**params)
    data = pd.DataFrame(
        {
            "x": df["cond"].cat.codes.to_numpy() + 1.0,
            "y": df["y"].to_numpy(),
            "PANEL": 1,
            "group": df["cond"].cat.codes.to_numpy() + 1,
        }
    )
    for col in ("fill",):
        if col in df:
            data[col] = df[col].to_numpy()
            data["group"] = (
                df["cond"].cat.codes.to_numpy() * 10 + pd.Categorical(df[col]).codes + 1
            )
    scales = SimpleNamespace(x=SimpleNamespace(final_limits=LEVELS))
    return s.compute_panel(data, scales)


@pytest.mark.parametrize(
    "ours, theirs", [("holm", "holm"), ("bh", "fdr_bh"), ("bonferroni", "bonferroni")]
)
def test_p_adjust_matches_statsmodels(ours, theirs):
    p = np.array([0.01, 0.04, 0.03, 0.2, 0.001, 0.5])
    np.testing.assert_allclose(p_adjust(p, ours), multipletests(p, method=theirs)[1])
    np.testing.assert_array_equal(p_adjust(p, None), p)
    with pytest.raises(ValueError):
        p_adjust(p, "sidak")


def test_format_p():
    assert [format_p(p) for p in (0.2, 0.05, 0.01, 0.001, 1e-4, 1e-9)] == [
        "ns", "*", "**", "***", "****", "****",
    ]
    assert format_p(0.01234, "p") == "p = 0.012"
    assert format_p(3.2e-5, "p", "p.adj") == "p.adj = 3.2e-5"


@pytest.mark.parametrize(
    "method, fn",
    [
        ("t-test", lambda a, b: stats.ttest_ind(a, b, equal_var=False).pvalue),
        ("student", lambda a, b: stats.ttest_ind(a, b).pvalue),
        ("mann-whitney", lambda a, b: stats.mannwhitneyu(a, b).pvalue),
    ],
)
def test_p_values_match_scipy(df, method, fn):
    out = compute(df, comparisons=[("WT", "KO")], method=method, p_adjust=None)
    a, b = (df.loc[df["cond"] == g, "y"] for g in ("WT", "KO"))
    assert out["p"].iloc[0] == pytest.approx(fn(a, b))
    assert (out["xmin"].iloc[0], out["xmax"].iloc[0]) == (1, 2)


def test_paired_tests(df):
    a, b = (df.loc[df["cond"] == g, "y"].to_numpy() for g in ("WT", "KO"))
    out = compute(df, comparisons=[("WT", "KO")], paired=True)
    assert out["p"].iloc[0] == pytest.approx(stats.ttest_rel(a, b).pvalue)
    out = compute(df, comparisons=[("WT", "KO")], paired=True, method="mann-whitney")
    assert out["p"].iloc[0] == pytest.approx(stats.wilcoxon(a, b).pvalue)


def test_all_pairs_adjusted_and_stacked_without_overlap(df):
    out = compute(df)
    assert len(out) == 6
    np.testing.assert_allclose(out["p_adj"], multipletests(out["p"], method="holm")[1])
    rows = out[["xmin", "xmax", "y"]].to_numpy()
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            (a0, a1, ya), (b0, b1, yb) = rows[i], rows[j]
            if a0 <= b1 and b0 <= a1:  # overlapping spans
                assert abs(ya - yb) > 1e-9
    # every bracket is above the data it spans
    for a0, a1, y in rows:
        covered = df.loc[df["cond"].cat.codes.between(a0 - 1, a1 - 1), "y"]
        assert y > covered.max()


def test_ref_group_and_hide_ns(df):
    out = compute(df, ref_group="WT")
    assert sorted(zip(out["xmin"], out["xmax"])) == [(1, 2), (1, 3), (1, 4)]
    hidden = compute(df, ref_group="WT", hide_ns=True, p_adjust=None)
    assert (hidden["p"] <= 0.05).all() and len(hidden) < 3


def test_label_type_and_bad_arguments(df):
    out = compute(df, comparisons=[("WT", "Dbl")], label_type="p")
    assert out["label"].iloc[0].startswith("p = ")
    with pytest.raises(TypeError):
        stat_compare_means(label="p")
    with pytest.raises(ValueError):
        stat_compare_means(method="anova")
    with pytest.raises(ValueError):
        compute(df, comparisons=[("WT", "Mutant")])


def test_within_dodged_groups(df):
    df = df.copy()
    df["fill"] = np.where(np.arange(len(df)) % 2, "ko", "wt")
    out = compute(df, within="fill")
    assert len(out) == 4  # one comparison per x category
    first = out.sort_values("xmin").iloc[0]
    assert (first["xmin"], first["xmax"]) == pytest.approx((1 - 0.225, 1 + 0.225))
    sub = df[df["cond"] == "WT"]
    a, b = (sub.loc[sub["fill"] == g, "y"] for g in ("ko", "wt"))
    assert first["p"] == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue)


def built(p):
    fig = p.draw()
    FigureCanvasAgg(fig).draw()
    return fig


def test_rendered_brackets_and_facets(df):
    df = df.assign(batch=np.arange(len(df)) % 2)
    p = (
        ggplot(df, aes("cond", "y"))
        + geom_boxplot()
        + stat_compare_means(comparisons=[("WT", "KO"), ("WT", "Dbl")])
        + facet_wrap("batch")
    )
    fig = built(p)
    for ax in fig.axes:
        lc = [c for c in ax.collections if isinstance(c, LineCollection)][-1]
        assert len(lc.get_segments()) == 2
        labels = [t.get_text() for t in ax.texts]
        assert len(labels) == 2
        # brackets fit inside the panel
        top = max(seg[:, 1].max() for seg in lc.get_segments())
        assert top < ax.get_ylim()[1]


def test_manual_brackets_by_name(df):
    man = pd.DataFrame(
        {"xmin": ["WT", "KO"], "xmax": ["Dbl", "Rescue"], "y": [5.0, 4.2], "label": ["a", "b"]}
    )
    p = (
        ggplot(df, aes("cond", "y"))
        + geom_boxplot()
        + geom_bracket(aes(xmin="xmin", xmax="xmax", y="y", label="label"), data=man, inherit_aes=False)
    )
    fig = built(p)
    lc = [c for c in fig.axes[0].collections if isinstance(c, LineCollection)][-1]
    spans = sorted((seg[0, 0], seg[2, 0]) for seg in lc.get_segments())
    assert spans == [(1, 4), (2, 3)]
