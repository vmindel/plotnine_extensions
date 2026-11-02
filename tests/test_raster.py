import io

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from plotnine import (
    aes,
    facet_wrap,
    geom_point,
    geom_smooth,
    ggplot,
    stat_identity,
)
from pypdf import PdfReader

from plotnine_extensions import RasterGroup, rasterise


@pytest.fixture
def df():
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "x": rng.normal(size=2000),
            "y": rng.normal(size=2000),
            "g": rng.integers(0, 3, 2000),
        }
    )


def pdf_images(p, **kwargs):
    buf = io.BytesIO()
    p.save(buf, format="pdf", width=4, height=3, verbose=False, **kwargs)
    buf.seek(0)
    page = PdfReader(buf).pages[0]
    return [im.image.size for im in page.images], buf.getbuffer().nbytes


def png_array(p):
    fig = p.draw()
    fig.set_dpi(72)
    FigureCanvasAgg(fig).draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def test_vector_baseline_has_no_images(df):
    images, _ = pdf_images(ggplot(df, aes("x", "y")) + geom_point())
    assert images == []


@pytest.mark.parametrize("dpi", [72, 300])
def test_layer_is_one_image_at_requested_dpi(df, dpi):
    p = ggplot(df, aes("x", "y")) + rasterise(geom_point(), dpi=dpi)
    images, _ = pdf_images(p)
    assert len(images) == 1
    w, h = images[0]
    # The image covers the points' extent, which is most of a 4x3 inch
    # figure; check the resolution, not the exact crop.
    assert 0.6 * 4 * dpi < w < 4 * dpi
    assert 0.5 * 3 * dpi < h < 3 * dpi


def test_dpi_is_independent_of_save_dpi(df):
    p = ggplot(df, aes("x", "y")) + rasterise(geom_point(), dpi=100)
    lo, _ = pdf_images(p, dpi=72)
    hi, _ = pdf_images(p, dpi=600)
    assert lo == hi


def test_dpi_none_uses_matplotlib_rasterisation(df):
    p = ggplot(df, aes("x", "y")) + rasterise(geom_point(), dpi=None)
    # dpi=None draws the artists unchanged, so they stay vector
    images, _ = pdf_images(p)
    assert images == []


def test_one_image_per_panel(df):
    p = (
        ggplot(df, aes("x", "y"))
        + rasterise(geom_point(), dpi=150)
        + facet_wrap("g")
    )
    images, _ = pdf_images(p)
    assert len(images) == 3


def test_only_rasterised_layer_becomes_image(df):
    p = (
        ggplot(df, aes("x", "y"))
        + rasterise(geom_point(), dpi=150)
        + geom_smooth(method="lm")
    )
    fig = p.draw()
    ax = fig.axes[0]
    groups = [a for a in ax.get_children() if isinstance(a, RasterGroup)]
    assert len(groups) == 1
    # The smooth line and ribbon stay ordinary children of the axes
    assert all(
        type(c).__name__ in {"PathCollection"} for c in groups[0].get_children()
    )


def pdf_size(p):
    buf = io.BytesIO()
    p.save(buf, format="pdf", width=4, height=3, verbose=False)
    return buf.getbuffer().nbytes


def test_smaller_file(df):
    big = pd.concat([df] * 20, ignore_index=True)
    vector = pdf_size(ggplot(big, aes("x", "y")) + geom_point())
    raster = pdf_size(
        ggplot(big, aes("x", "y")) + rasterise(geom_point(), dpi=72)
    )
    assert raster < vector / 10


def test_png_unchanged(df):
    base = png_array(ggplot(df, aes("x", "y")) + geom_point())
    rast = png_array(ggplot(df, aes("x", "y")) + rasterise(geom_point()))
    np.testing.assert_array_equal(base, rast)


def test_svg_embeds_image(df):
    buf = io.StringIO()
    p = ggplot(df, aes("x", "y")) + rasterise(geom_point(), dpi=100)
    fig = p.draw()
    fig.savefig(buf, format="svg")
    assert buf.getvalue().count("<image") == 1


def test_bbox_inches_tight(df):
    p = ggplot(df, aes("x", "y")) + rasterise(geom_point(), dpi=100)
    images, _ = pdf_images(p, bbox_inches="tight")
    assert len(images) == 1


def test_whole_plot_with_layer_filter(df):
    p = ggplot(df, aes("x", "y")) + geom_point() + geom_smooth(method="lm")
    q = rasterise(p, dpi=100, layers=["point"])
    assert "draw_layer" not in vars(p.layers[0].geom), "original modified"
    assert "draw_layer" in vars(q.layers[0].geom)
    assert "draw_layer" not in vars(q.layers[1].geom)
    images, _ = pdf_images(q)
    assert len(images) == 1


def test_stat_and_list(df):
    p = ggplot(df, aes("x", "y")) + rasterise(stat_identity(geom="point"))
    assert len(pdf_images(p)[0]) == 1
    p = ggplot(df, aes("x", "y")) + rasterise([geom_point(), geom_point()])
    assert len(pdf_images(p)[0]) == 2


def test_bad_arguments(df):
    with pytest.raises(ValueError):
        rasterise(geom_point(), dpi=0)
    with pytest.raises(TypeError):
        rasterise(geom_point(), layers=["point"])
    with pytest.raises(TypeError):
        rasterise("geom_point")
