"""Command line: draw a gantt from a ``.yml`` file.

Usage: ``yml2gantt project.yml [-o chart.pdf] [--no-show]``
"""

import argparse
import sys
from pathlib import Path

import yaml

from . import __version__, load_yaml
from .errors import GanttError, did_you_mean


def _check_output(output):
    """Check the output file before drawing: format and folder."""
    from matplotlib.backend_bases import FigureCanvasBase

    formats = FigureCanvasBase.get_supported_filetypes()
    ext = output.suffix[1:].lower()
    if not ext:
        raise GanttError(f"the output file {str(output)!r} has no extension: "
                         f"add one to choose the format, e.g. .pdf, .png, "
                         f".svg")
    if ext not in formats:
        raise GanttError(f"unknown output format {ext!r}"
                         f"{did_you_mean(ext, formats)}. Supported: "
                         f"{', '.join(sorted(formats))}")
    folder = output.parent
    if not folder.is_dir():
        raise GanttError(f"the folder {str(folder)!r} of the output file does "
                         f"not exist")


def _yaml_message(err):
    """Readable text for a YAML syntax error."""
    mark = getattr(err, "problem_mark", None)
    problem = getattr(err, "problem", None) or str(err)
    if isinstance(err, yaml.constructor.ConstructorError):
        text = problem
    else:
        text = f"invalid YAML: {problem}"
    if mark is not None:
        text = f"line {mark.line + 1}, column {mark.column + 1}: {text}"
        snippet = mark.get_snippet()
        if snippet:
            text += "\n" + snippet
    context = getattr(err, "context", None)
    if context and "mapping" not in context:
        text += f"\n  ({context})"
    if "'\\t'" in str(problem) or "tab" in str(problem):
        text += "\n  YAML does not allow tabs for indentation: use spaces"
    return text


def _fail(parser, file, message):
    parser.exit(1, f"yml2gantt: error in {file}: {message}\n")


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
    output = Path(args.output) if args.output else \
        Path(args.file).with_suffix(".pdf")

    try:
        _check_output(output)
    except GanttError as err:
        parser.exit(1, f"yml2gantt: error: {err}\n")

    try:
        gantt = load_yaml(args.file)
        for warning in gantt.check():
            print(f"yml2gantt: warning: {warning}", file=sys.stderr)
        fig, _ = gantt.draw()
    except FileNotFoundError:
        parser.exit(1, f"yml2gantt: error: no file {args.file!r}\n")
    except IsADirectoryError:
        parser.exit(1, f"yml2gantt: error: {args.file!r} is a folder, not a "
                       f"file\n")
    except UnicodeDecodeError:
        _fail(parser, args.file, "the file is not UTF-8 text")
    except OSError as err:
        parser.exit(1, f"yml2gantt: error: cannot read {args.file!r}: "
                       f"{err.strerror}\n")
    except yaml.YAMLError as err:
        _fail(parser, args.file, _yaml_message(err))
    except (ValueError, TypeError) as err:
        # GanttError is a ValueError; the rest would be a bug, but the
        # message is still more useful than a traceback.
        _fail(parser, args.file, err)

    try:
        fig.savefig(output)
    except OSError as err:
        parser.exit(1, f"yml2gantt: error: cannot write {str(output)!r}: "
                       f"{err.strerror or err}\n")
    print(f"Saved {output}")
    if not args.no_show:
        import matplotlib.pyplot as plt
        plt.show()


if __name__ == "__main__":
    main()
