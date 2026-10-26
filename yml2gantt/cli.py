"""Command line: draw a gantt from a ``.yml`` file.

Usage: ``yml2gantt project.yml [-o chart.pdf] [--no-show]``
"""

import argparse
from pathlib import Path

import yaml

from . import __version__, load_yaml


def main(argv=None):
    """Parse the arguments, draw, save and show the gantt.

    Parameters
    ----------
    argv : list of str, optional
        Arguments. Default: ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(
        prog="yml2gantt",
        description="Draw a gantt chart from a .yml file.")
    parser.add_argument("file", help="gantt description (.yml)")
    parser.add_argument("-o", "--output",
                        help="output file, the extension sets the format "
                             "(default: <file>.pdf)")
    parser.add_argument("--no-show", action="store_true",
                        help="do not open a window")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        fig, _ = load_yaml(args.file).draw()
    except (OSError, ValueError, TypeError, yaml.YAMLError) as err:
        parser.exit(1, f"yml2gantt: error: {err}\n")
    output = args.output or Path(args.file).with_suffix(".pdf")
    fig.savefig(output)
    print(f"Saved {output}")
    if not args.no_show:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()
