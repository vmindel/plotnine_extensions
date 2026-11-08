"""
ggplot2-ecosystem extensions for plotnine
"""

from .curve import geom_curve
from .distributions import (
    geom_pointinterval,
    geom_raincloud,
    position_jitternudge,
    stat_halfeye,
    stat_pointinterval,
)
from .hex import geom_hex, hex_bins, stat_bin_hex
from .logo import LOGO_PALETTES, geom_logo, logo_data
from .raster import RasterGroup, rasterise, rasterize
from .repel import geom_label_repel, geom_text_repel
from .signif import format_p, geom_bracket, p_adjust, stat_compare_means
from .themes import (
    background_grid,
    bgcolor,
    border,
    clean_theme,
    font,
    grids,
    panel_border,
    rotate_x_text,
    rotate_y_text,
    rremove,
    theme_classic2,
    theme_cowplot,
    theme_half_open,
    theme_map,
    theme_minimal_grid,
    theme_minimal_hgrid,
    theme_minimal_vgrid,
    theme_nothing,
    theme_pubclean,
    theme_pubr,
)

__all__ = [
    "format_p",
    "geom_bracket",
    "p_adjust",
    "stat_compare_means",
    "geom_pointinterval",
    "geom_raincloud",
    "position_jitternudge",
    "stat_halfeye",
    "stat_pointinterval",
    "geom_curve",
    "geom_hex",
    "hex_bins",
    "stat_bin_hex",
    "LOGO_PALETTES",
    "geom_logo",
    "logo_data",
    "RasterGroup",
    "geom_label_repel",
    "geom_text_repel",
    "rasterise",
    "rasterize",
    "theme_pubr",
    "theme_pubclean",
    "theme_classic2",
    "clean_theme",
    "rotate_x_text",
    "rotate_y_text",
    "rremove",
    "grids",
    "border",
    "bgcolor",
    "font",
    "theme_cowplot",
    "theme_half_open",
    "theme_minimal_grid",
    "theme_minimal_hgrid",
    "theme_minimal_vgrid",
    "theme_map",
    "theme_nothing",
    "background_grid",
    "panel_border",
]
