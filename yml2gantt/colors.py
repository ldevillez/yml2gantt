"""Color helpers."""

import colorsys
from collections import defaultdict

import matplotlib.colors as mc
from matplotlib import rcParams


def lighten_color(color, amount=0.5):
    """Lighten a color.

    Parameters
    ----------
    color : str or tuple
        Matplotlib color (name, hex or RGB).
    amount : float, optional
        0 gives white, 1 keeps the color.

    Returns
    -------
    tuple of float
        RGB color.
    """
    c = colorsys.rgb_to_hls(*mc.to_rgb(mc.cnames.get(color, color)))
    return colorsys.hls_to_rgb(c[0], 1 - amount * (1 - c[1]), c[2])


def get_color_cycler():
    """Map each key to the next color of the matplotlib cycle.

    Returns
    -------
    collections.defaultdict
        ``cycler[key]["color"]`` gives the color of ``key``.
    """
    cycle = rcParams["axes.prop_cycle"]()
    return defaultdict(lambda: next(cycle))
