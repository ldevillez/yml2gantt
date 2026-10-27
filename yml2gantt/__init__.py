"""Draw gantt charts from a ``.yml`` file or from Python."""

from importlib.metadata import PackageNotFoundError, version

from .errors import GanttError, Issue
from .io import add_tasks, from_dict, load_yaml
from .model import Gantt, Task
from .plot import draw
from .scale import SCALES, Scale

try:
    __version__ = version("yml2gantt")
except PackageNotFoundError:  # running from a source checkout
    __version__ = "0+unknown"

__all__ = ["Gantt", "Task", "Scale", "SCALES", "draw", "load_yaml",
           "from_dict", "add_tasks", "GanttError", "Issue", "__version__"]
