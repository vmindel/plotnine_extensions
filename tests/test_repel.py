import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from plotnine import aes, facet_wrap, geom_point, ggplot, scale_x_reverse
from plotnine.exceptions import PlotnineWarning

from plotnine_extensions import geom_label_repel, geom_text_repel
from plotnine_extensions.repel import RepelLabels
from plotnine_extensions.repel._solver import count_overlaps, repel


def boxes_overlap(c, size):
    half = size / 2
    d = np.abs(c[:, None, :] - c[None, :, :])
    hit = (d[..., 0] < half[:, None, 0] + half[None, :, 0]) & (
        d[..., 1] < half[:, None, 1] + half[None, :, 1]
    )
    np.fill_diagonal(hit, False)
    return hit.any()


def box_point_overlap(c, size, points, r):
    half = size / 2
    d = np.abs(c[:, None, :] - points[None, :, :])
    return (
        (d[..., 0] < half[:, None, 0] + r) & (d[..., 1] < half[:, None, 1] + r)
    ).any()


# Solver


@pytest.mark.parametrize("seed", range(5))
def test_solver_removes_overlaps(seed):
    rng = np.random.default_rng(seed)
    n = 25
    pts = rng.normal(400, 60, size=(n, 2))
    size = np.column_stack([rng.uniform(30, 60, n), np.full(n, 12.0)])
    res = repel(pts, size, pts, np.full(n, 2.0), (0, 800, 0, 800), max_time=5)
    assert res.converged
    assert not boxes_overlap(res.centres, size)
    assert not box_point_overlap(res.centres, size, pts, 2.0)


def test_solver_stays_in_bounds():
    rng = np.random.default_rng(1)
    n = 20
    pts = rng.uniform(0, 200, size=(n, 2))
    size = np.full((n, 2), 30.0)
    res = repel(pts, size, pts, np.full(n, 2.0), (0, 200, 0, 200), max_time=5)
    c = res.centres
    assert (c - 15 >= -1e-6).all() and (c + 15 <= 200 + 1e-6).all()


def test_label_on_edge_escapes_sideways():
    # Point on the bottom edge: the label cannot go below it
    pts = np.array([[100.0, 0.0]])
    size = np.array([[40.0, 12.0]])
    res = repel(pts, size, pts, np.array([3.0]), (0, 200, 0, 200))
    assert res.converged
    assert not box_point_overlap(res.centres, size, pts, 3.0)


@pytest.mark.parametrize("direction, fixed", [("x", 1), ("y", 0)])
def test_direction(direction, fixed):
    rng = np.random.default_rng(2)
    n = 10
    pts = np.column_stack([np.full(n, 400.0), rng.uniform(380, 420, n)])
    if direction == "y":
        pts = pts[:, ::-1].copy()
    size = np.full((n, 2), 20.0)
    res = repel(pts, size, pts, np.full(n, 1.0), (0, 800, 0, 800), direction=direction)
    np.testing.assert_allclose(res.centres[:, fixed], pts[:, fixed], atol=1e-6)


def test_seed_is_deterministic():
    rng = np.random.default_rng(3)
    pts = rng.normal(100, 20, size=(15, 2))
    size = np.full((15, 2), 20.0)
    a = repel(pts, size, pts, np.full(15, 1.0), (0, 200, 0, 200), seed=7)
    b = repel(pts, size, pts, np.full(15, 1.0), (0, 200, 0, 200), seed=7)
    np.testing.assert_array_equal(a.centres, b.centres)


def test_count_overlaps_keeps_earlier_rows():
    c = np.zeros((5, 2))
    half = np.full((5, 2), 10.0)
    keep = count_overlaps(c, half, np.zeros((0, 2)), np.zeros(0), np.zeros(5, int), 2)
    assert keep.tolist() == [True, True, True, False, False]
    keep = count_overlaps(c, half, np.zeros((0, 2)), np.zeros(0), np.zeros(5, int), np.inf)
    assert keep.all()


# Geoms


@pytest.fixture
def df():
    rng = np.random.default_rng(4)
    n = 200
    d = pd.DataFrame(
        {"x": rng.normal(size=n), "y": rng.normal(size=n), "g": np.arange(n) % 2}
    )
    d["lab"] = [f"gene{i}" if i < 25 else "" for i in range(n)]
    return d


def repel_artists(p, width=5, height=4):
    p = p + __import__("plotnine").theme(figure_size=(width, height))
    fig = p.draw()
    FigureCanvasAgg(fig).draw()
    return fig, [
        a
        for ax in fig.axes
        for a in ax.get_children()
        if isinstance(a, RepelLabels)
    ]


def drawn_boxes(art):
    lay = art.last_layout
    return lay.centres[lay.keep], art._text_size[lay.keep]


@pytest.mark.parametrize("geom", [geom_text_repel, geom_label_repel])
def test_labels_do_not_overlap(df, geom):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_point() + geom(
        max_overlaps=np.inf, max_time=20
    )
    fig, (art,) = repel_artists(p)
    centres, size = drawn_boxes(art)
    assert art.last_layout.keep.sum() == 25
    assert art.last_layout.converged
    assert not boxes_overlap(centres, size)
    x0, y0, x1, y1 = art._ax.bbox.extents
    assert (centres[:, 0] - size[:, 0] / 2 >= x0 - 1).all()
    assert (centres[:, 1] + size[:, 1] / 2 <= y1 + 1).all()


def test_empty_and_missing_labels_still_repel(df):
    df.loc[30, "lab"] = None
    p = ggplot(df, aes("x", "y", label="lab")) + geom_text_repel()
    _, (art,) = repel_artists(p)
    # every row is an obstacle, only the 25 named rows are labels
    assert len(art._points) == len(df)
    assert len(art._texts) == 25


def test_one_artist_per_panel(df):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_text_repel() + facet_wrap("g")
    _, arts = repel_artists(p)
    assert len(arts) == 2


def test_layout_follows_figure_size(df):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_text_repel()
    _, (small,) = repel_artists(p, 4, 3)
    _, (big,) = repel_artists(p, 8, 6)
    assert not np.allclose(
        small.last_layout.centres[:3], big.last_layout.centres[:3]
    )


def test_nudge_moves_label_not_point(df):
    d = df.head(3).assign(lab=["a", "b", "c"])
    p = ggplot(d, aes("x", "y", label="lab")) + geom_text_repel(nudge_y=1)
    _, (art,) = repel_artists(p)
    np.testing.assert_allclose(art._points, d[["x", "y"]].to_numpy())
    np.testing.assert_allclose(art._nudged[:, 1], d["y"].to_numpy() + 1)


def test_xlim_keeps_labels_right_of_limit(df):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_text_repel(xlim=(0, None))
    _, (art,) = repel_artists(p)
    centres, size = drawn_boxes(art)
    xpix0 = art._ax.transData.transform([[0, 0]])[0, 0]
    assert (centres[:, 0] - size[:, 0] / 2 >= xpix0 - 3.5).all()


def test_label_region_away_from_points(df):
    # Points at x < 0, labels confined to x > 1: every label is drawn
    d = pd.DataFrame(
        {"x": -np.arange(5.0) - 1, "y": np.arange(5.0), "lab": list("abcde")}
    )
    p = (
        ggplot(d, aes("x", "y", label="lab"))
        + geom_text_repel(xlim=(1, None), direction="y")
        + __import__("plotnine").scale_x_continuous(limits=(-6, 3))
    )
    _, (art,) = repel_artists(p)
    centres, size = drawn_boxes(art)
    assert art.last_layout.keep.all()
    xpix1 = art._ax.transData.transform([[1, 0]])[0, 0]
    assert (centres[:, 0] - size[:, 0] / 2 >= xpix1 - 3.5).all()


def test_xlim_with_reversed_scale(df):
    p = (
        ggplot(df, aes("x", "y", label="lab"))
        + geom_text_repel(xlim=(0, None))
        + scale_x_reverse()
    )
    _, (art,) = repel_artists(p)
    centres, size = drawn_boxes(art)
    xpix0 = art._ax.transData.transform([[0, 0]])[0, 0]
    # x >= 0 is now the left part of the panel
    assert (centres[:, 0] + size[:, 0] / 2 <= xpix0 + 3.5).all()


def test_max_overlaps_drops_unplaceable_labels():
    # 40 labels on one point in a tiny panel cannot all be placed
    d = pd.DataFrame(
        {"x": np.zeros(40), "y": np.zeros(40), "lab": [f"label{i}" for i in range(40)]}
    )
    p = ggplot(d, aes("x", "y", label="lab")) + geom_text_repel(
        max_overlaps=0, max_time=0.2
    )
    with pytest.warns(PlotnineWarning, match="not drawn"):
        _, (art,) = repel_artists(p, 2, 1.5)
    kept = art.last_layout.keep
    assert 0 < kept.sum() < 40
    # earlier rows have priority
    assert kept[0]


def test_max_overlaps_keeps_placeable_labels(df):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_point() + geom_text_repel()
    _, (art,) = repel_artists(p)
    assert art.last_layout.keep.sum() == 25


def test_rejects_adjust_text():
    with pytest.raises(ValueError):
        geom_text_repel(adjust_text={})


def test_bad_direction():
    with pytest.raises(ValueError):
        geom_text_repel(direction="z")


def test_saves_to_vector_formats(df, tmp_path):
    p = ggplot(df, aes("x", "y", label="lab")) + geom_point() + geom_label_repel(arrow={})
    for ext in ("pdf", "svg", "png"):
        p.save(tmp_path / f"f.{ext}", width=4, height=3, verbose=False)
        assert (tmp_path / f"f.{ext}").stat().st_size > 0
