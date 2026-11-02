import io

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from plotnine import aes, facet_wrap, ggplot

from plotnine_extensions import geom_logo, logo_data


def built(p):
    fig = p.draw()
    FigureCanvasAgg(fig).draw()
    return fig


def stacked(data):
    """Run geom_logo's stacking on a small table."""
    g = geom_logo()
    df = data.rename(columns={"position": "x", "height": "y", "letter": "label"})
    df["PANEL"] = 1
    return g.setup_data(df).set_index("label")


def test_positive_letters_stack_tallest_on_top():
    out = stacked(
        pd.DataFrame({"position": 1, "letter": list("ACG"), "height": [0.2, 1.0, 0.5]})
    )
    assert out.loc["A", "ymin"] == 0 and out.loc["A", "ymax"] == pytest.approx(0.2)
    assert out.loc["G", "ymin"] == pytest.approx(0.2)
    assert out.loc["C", "ymax"] == pytest.approx(1.7)


def test_negative_letters_stack_down_largest_lowest():
    out = stacked(
        pd.DataFrame({"position": 1, "letter": list("ACT"), "height": [-0.2, -1.0, 0.3]})
    )
    assert out.loc["A", "ymax"] == 0 and out.loc["A", "ymin"] == pytest.approx(-0.2)
    assert out.loc["C", "ymin"] == pytest.approx(-1.2)
    assert out.loc["T", "ymin"] == 0


def test_zero_and_missing_heights_dropped():
    out = stacked(
        pd.DataFrame({"position": 1, "letter": list("ACG"), "height": [0, np.nan, 1]})
    )
    assert list(out.index) == ["G"]


def test_bits_of_a_conserved_column():
    seqs = ["A"] * 20
    d = logo_data(seqs)
    a = d.query("letter == 'A'")["height"].iloc[0]
    # 2 bits minus the small-sample correction (4 - 1) / (2 ln2 * 20)
    assert a == pytest.approx(2 - 3 / (2 * np.log(2) * 20))
    assert logo_data(seqs, correction=False).query("letter == 'A'")["height"].iloc[0] == 2


def test_bits_of_a_uniform_column_is_zero():
    d = logo_data(["A", "C", "G", "T"] * 5)
    assert np.allclose(d["height"], 0)


def test_probability_and_counts():
    seqs = ["AC", "AG", "AG", "TG"]
    p = logo_data(seqs, method="probability")
    assert np.allclose(p.groupby("position")["height"].sum(), 1)
    c = logo_data(seqs, method="counts")
    assert c.query("position == 2 and letter == 'G'")["height"].iloc[0] == 3


def test_gaps_and_n_are_ignored():
    d = logo_data(["A-N", "AC-"], method="counts")
    assert set(d["letter"]) == set("ACGT")
    assert d.query("position == 3")["height"].sum() == 0


def test_contribution_scores_masked_by_sequence():
    m = np.arange(12, dtype=float).reshape(3, 4) - 6
    d = logo_data(m, alphabet="ACGT", method="none", sequence="AGT")
    kept = d[d["height"] != 0]
    # row 0: A=-6; row 1 (C=-1 is zero-masked) G=0 is dropped as zero; row 2: T=5
    assert kept["letter"].tolist() == ["A", "T"]
    assert kept["height"].tolist() == [-6.0, 5.0]


def test_dataframe_matrix_uses_columns_as_alphabet():
    m = pd.DataFrame({"A": [1.0, 0], "C": [0, 1.0]})
    d = logo_data(m, method="none", start=10)
    assert d["position"].tolist() == [10, 10, 11, 11]
    assert d["letter"].tolist() == ["A", "C", "A", "C"]


def test_protein_alphabet_inferred():
    d = logo_data(["MKV", "MRV"], method="probability")
    assert set(d["letter"]) == set("ACDEFGHIKLMNPQRSTVWY")


def test_errors():
    with pytest.raises(ValueError, match="aligned"):
        logo_data(["AC", "A"])
    with pytest.raises(ValueError, match="alphabet"):
        logo_data(np.ones((2, 4)))
    with pytest.raises(ValueError, match="method"):
        logo_data(["A"], method="entropy")
    with pytest.raises(ValueError, match="matrix"):
        logo_data(["A"], method="none")
    with pytest.raises(ValueError, match="length"):
        logo_data(np.ones((2, 4)), alphabet="ACGT", method="none", sequence="A")


def test_draws_one_glyph_per_nonzero_letter():
    d = logo_data(["ACGT", "ACGA", "ACCT"], method="probability")
    p = ggplot(d, aes("position", "height", label="letter")) + geom_logo()
    fig = built(p)
    (col,) = fig.axes[0].collections
    assert len(col.get_paths()) == (d["height"] > 0).sum()
    # y-axis covers the stacked heights
    assert fig.axes[0].get_ylim()[1] >= 1


def test_negative_heights_extend_the_axis_and_mapped_fill_and_facets():
    m = np.array([[1.0, -2, 0, 0], [0, 0, 0.5, -0.5]])
    d = pd.concat(
        [
            logo_data(m, alphabet="ACGT", method="none").assign(model="a"),
            logo_data(-m, alphabet="ACGT", method="none").assign(model="b"),
        ]
    )
    p = (
        ggplot(d, aes("position", "height", label="letter", fill="letter"))
        + geom_logo()
        + facet_wrap("model")
    )
    fig = built(p)
    assert fig.axes[0].get_ylim()[0] <= -2
    buf = io.BytesIO()
    p.save(buf, format="pdf", width=5, height=2, verbose=False)
    assert buf.getbuffer().nbytes > 0
