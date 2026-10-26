"""Loading a gantt from a dict or a ``.yml`` file."""

from .model import Gantt

_GANTT_KEYS = {"start", "end", "duration", "scale", "title", "show_today",
               "label_format", "label_every", "step", "now", "now_label"}
_TASK_KEYS = {"name", "start", "duration", "end", "color", "subtasks",
              "milestone", "milestones",
              "label", "segments"}
_SEGMENT_KEYS = {"start", "duration", "end", "color", "label"}
_MARKER_KEYS = {"name", "at", "color"}


def _clean(item, allowed, where):
    """Lowercase the keys, accept ``task`` for ``name`` and check them."""
    item = {k.lower(): v for k, v in item.items()}
    if "task" in item:
        item["name"] = item.pop("task")
    unknown = set(item) - allowed
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    return item


def _add_markers(task, markers):
    for raw in markers or []:
        if isinstance(raw, str):
            raw = {"name": raw}
        task.add_milestone(**_clean(raw, _MARKER_KEYS,
                                    f"milestone of {task.name!r}"))


def _add_segments(task, segments):
    for raw in segments or []:
        task.add_segment(**_clean(raw, _SEGMENT_KEYS,
                                  f"segment of {task.name!r}"))


def add_tasks(gantt, tasks):
    """Add tasks described as dicts.

    Parameters
    ----------
    gantt : Gantt
        Gantt to fill.
    tasks : list of dict
        Keys: ``name``, ``start``, ``duration`` or ``end``, ``color``,
        ``label`` (text in the bar, default ``name``),
        ``milestone`` (true: a point at ``start``), ``milestones`` (on the
        bar: names, or dicts with ``name``, ``at`` and ``color``, see
        `Task.add_milestone`), ``segments`` (pieces of bar on the same
        row, dicts with ``start``, ``duration`` or ``end``, ``color``,
        ``label``, start relative to the task), ``subtasks`` (same keys,
        start relative to the parent).

    Returns
    -------
    Gantt
        The same gantt.
    """
    for raw in tasks:
        t = _clean(raw, _TASK_KEYS, "task")
        subtasks = t.pop("subtasks", None) or []
        markers = t.pop("milestones", None)
        segments = t.pop("segments", None)
        if t.get("milestone") and subtasks:
            raise ValueError(f"Milestone {t.get('name')!r} cannot have subtasks")
        task = gantt.add_task(**t)
        _add_segments(task, segments)
        _add_markers(task, markers)
        for raw_st in subtasks:
            st = _clean(raw_st, _TASK_KEYS - {"subtasks"},
                        f"subtask of {task.name!r}")
            markers = st.pop("milestones", None)
            segments = st.pop("segments", None)
            sub = task.add_subtask(**st)
            _add_segments(sub, segments)
            _add_markers(sub, markers)
    return gantt


def from_dict(data):
    """Build a gantt from a dict.

    Parameters
    ----------
    data : dict
        ``{"gantt": {...}, "tasks": [...]}``, see `Gantt` and `add_tasks`.

    Returns
    -------
    Gantt
    """
    settings = _clean(data.get("gantt", {}), _GANTT_KEYS, "gantt")
    return add_tasks(Gantt(**settings), data.get("tasks", []))


def load_yaml(path):
    """Build a gantt from a ``.yml`` file.

    Parameters
    ----------
    path : str or path-like
        File with a ``gantt`` section and a ``tasks`` list.

    Returns
    -------
    Gantt
    """
    import yaml

    with open(path, encoding="utf-8") as f:
        return from_dict(yaml.safe_load(f) or {})
