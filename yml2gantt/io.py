"""Loading a gantt from a dict or a ``.yml`` file.

Every problem found in the description is reported together, with the
line of the element in the file, in a single `GanttError`.
"""

from .errors import GanttError, Issue, describe, did_you_mean
from .model import Gantt

_TOP_KEYS = {"gantt", "tasks"}
_GANTT_KEYS = {"start", "end", "duration", "scale", "title", "show_today",
               "label_format", "label_every", "step", "now", "now_label"}
_TASK_KEYS = {"name", "start", "duration", "end", "color", "subtasks",
              "milestone", "milestones",
              "label", "segments"}
_SEGMENT_KEYS = {"start", "duration", "end", "color", "label"}
_MARKER_KEYS = {"name", "at", "color"}
# Keys whose empty value means "none" (or "defaults" for 'gantt').
_EMPTY_OK = {"gantt", "tasks", "subtasks", "milestones", "segments"}

_EXAMPLES = {
    "task": "{name: Write, duration: 3}",
    "subtask": "{name: Draft, duration: 3}",
    "segment": "{start: 0, duration: 3}",
    "milestone": "{name: Review, at: 50%}",
}


class _Report:
    """Collects the problems found while loading."""

    def __init__(self):
        self.issues = []

    def add(self, message, where=None, line=None):
        self.issues.append(Issue(message, where, line))

    def capture(self, err, where, line):
        """Record a `GanttError` (or another value error) of an element.

        ``where`` replaces the location given by the model: it holds the
        full path in the file (task > subtask > milestone).
        """
        issues = getattr(err, "issues", None) or [Issue(str(err))]
        for i in issues:
            self.add(i.message, where, i.line or line)

    def raise_if_any(self):
        if self.issues:
            raise GanttError(self.issues)


def _line(item, default=None):
    """Line of a mapping read from a file (see `load_yaml`)."""
    return getattr(item, "line", None) or default


def _name_of(raw):
    """Name of a task description, before it is checked."""
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(k, str) and k.strip().lower() in ("name", "task"):
                if isinstance(v, (str, int, float)) and not isinstance(v, bool):
                    return str(v)
    return None


def _clean(item, allowed, where, line, report, kind):
    """Check the keys of a mapping.

    Lowercases the keys and accepts ``task`` for ``name``.

    Returns
    -------
    dict or None
        The mapping with clean keys (problems left out), or ``None`` when
        ``item`` is not a mapping.
    bool
        True if no problem was found.
    """
    if not isinstance(item, dict):
        hint = (" (in YAML, write a mapping as 'key: value' lines, or "
                f"{_EXAMPLES[kind]})" if kind in _EXAMPLES else "")
        report.add(f"expected a mapping of keys, got {describe(item)}{hint}",
                   where, line)
        return None, False
    out, ok = {}, True
    for key, value in item.items():
        if not isinstance(key, str):
            report.add(f"key {key!r} is not a name (keys are words such as "
                       f"'start')", where, line)
            ok = False
            continue
        k = key.strip().lower()
        if k == "task" and "name" in allowed:
            k = "name"
        if k not in allowed:
            if k == "subtasks" and kind == "subtask":
                msg = ("subtasks go only one level deep: a subtask cannot "
                       "have 'subtasks'")
            else:
                msg = (f"unknown key {key!r}{did_you_mean(k, allowed)}. "
                       f"Allowed keys: {', '.join(sorted(allowed))}")
            report.add(msg, where, line)
            ok = False
            continue
        if k in out:
            report.add(f"key {key!r} is given twice (keys are not case "
                       f"sensitive, and 'task' means 'name')", where, line)
            ok = False
            continue
        if value is None and k not in _EMPTY_OK:
            msg = f"'{k}' has no value"
            if k == "color":
                msg += (": a hex color must be in quotes, color: \"#3366cc\" "
                        "(an unquoted # starts a comment in YAML)")
            else:
                msg += ": give one, or remove the key"
            report.add(msg, where, line)
            ok = False
            continue
        out[k] = value
    return out, ok


def _as_list(value, key, where, line, report):
    """A list value; reports anything else."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    report.add(f"'{key}' must be a list, got {describe(value)} (in YAML, "
               f"start each item with '- ', or write [a, b])", where, line)
    return []


def _add_milestones(task, markers, where, line, report):
    for i, raw in enumerate(_as_list(markers, "milestones", where, line,
                                     report), start=1):
        if isinstance(raw, str):
            raw = {"name": raw}
        name = _name_of(raw)
        here = f"{where} > milestone {name!r}" if name else \
            f"{where} > milestone #{i}"
        mline = _line(raw, line)
        m, ok = _clean(raw, _MARKER_KEYS, here, mline, report, "milestone")
        if not ok:
            continue
        if "name" not in m:
            report.add("the milestone has no 'name'", here, mline)
            continue
        try:
            task.add_milestone(**m)
        except (ValueError, TypeError) as err:
            report.capture(err, here, mline)


def _add_segments(task, segments, where, line, report):
    for i, raw in enumerate(_as_list(segments, "segments", where, line,
                                     report), start=1):
        here = f"{where} > segment #{i}"
        sline = _line(raw, line)
        s, ok = _clean(raw, _SEGMENT_KEYS, here, sline, report, "segment")
        if not ok:
            continue
        try:
            task.add_segment(**s)
        except (ValueError, TypeError) as err:
            report.capture(err, here, sline)


def _add_task(gantt, raw, index, report, parent=None, parent_where=None,
              parent_line=None):
    """Add one task (or subtask of ``parent``), reporting its problems."""
    kind = "task" if parent is None else "subtask"
    name = _name_of(raw)
    where = f"{kind} {name!r}" if name else f"{kind} #{index}"
    if parent_where:
        where = f"{parent_where} > {where}"
    line = _line(raw, parent_line)

    allowed = _TASK_KEYS if parent is None else _TASK_KEYS - {"subtasks"}
    t, ok = _clean(raw, allowed, where, line, report, kind)
    if t is None:
        return
    subtasks = _as_list(t.pop("subtasks", None), "subtasks", where, line,
                        report)
    markers = t.pop("milestones", None)
    segments = t.pop("segments", None)
    if "name" not in t:
        report.add(f"the {kind} has no 'name'", where, line)
        return
    if t.get("milestone") is True:
        extra = [k for k, v in (("subtasks", subtasks), ("milestones", markers),
                                ("segments", segments)) if v]
        if extra:
            report.add(f"a milestone row is a single point in time: it "
                       f"cannot have {', '.join(repr(k) for k in extra)}",
                       where, line)
            return
    try:
        task = (gantt.add_task(**t) if parent is None
                else parent.add_subtask(**t))
    except (ValueError, TypeError) as err:
        report.capture(err, where, line)
        return

    if segments and subtasks:
        report.add("a task cannot have both 'segments' and 'subtasks'",
                   where, line)
        return
    _add_segments(task, segments, where, line, report)
    for i, raw_st in enumerate(subtasks, start=1):
        _add_task(gantt, raw_st, i, report, task, where, line)
    _add_milestones(task, markers, where, line, report)

    # Only when the task itself is fine: avoids a second error caused by
    # a misspelled 'duration'.
    if (ok and not task.milestone and task.duration is None
            and not segments and not subtasks):
        report.add(f"the {kind} has no length: give 'duration' or 'end', or "
                   f"add 'subtasks' or 'segments' (or 'milestone: true' for "
                   f"a single point in time)", where, line)


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

    Raises
    ------
    GanttError
        Listing every problem found.
    """
    report = _Report()
    for i, raw in enumerate(_as_list(tasks, "tasks", None, None, report),
                            start=1):
        _add_task(gantt, raw, i, report)
    report.raise_if_any()
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

    Raises
    ------
    GanttError
        Listing every problem found.
    """
    report = _Report()
    if data is None:
        raise GanttError("the description is empty: it needs a 'gantt' "
                         "section and a 'tasks' list")
    top, _ = _clean(data, _TOP_KEYS, "top level", _line(data), report, "top")
    if top is None:
        report.issues[-1].message += (
            ": the file needs a 'gantt' section and a 'tasks' list")
        report.raise_if_any()
    raw_gantt = top.get("gantt") or {}
    where, line = "'gantt' section", _line(raw_gantt, _line(data))
    settings, _ = _clean(raw_gantt, _GANTT_KEYS, where, line, report, "gantt")
    gantt = None
    if settings is not None:
        try:
            gantt = Gantt(**settings)
        except (ValueError, TypeError) as err:
            report.capture(err, where, line)
    if gantt is None:
        # Tasks cannot be checked without a time scale.
        report.raise_if_any()
    if "tasks" not in top:
        report.add("there is no 'tasks' list: add one with the rows of the "
                   "chart", "top level", _line(data))
    for i, raw in enumerate(_as_list(top.get("tasks"), "tasks", "top level",
                                     _line(data), report), start=1):
        _add_task(gantt, raw, i, report)
    report.raise_if_any()
    return gantt


def _loader():
    """A safe YAML loader that records lines and refuses duplicate keys."""
    import yaml
    from yaml.constructor import ConstructorError

    class Map(dict):
        line = None

    class Loader(yaml.SafeLoader):
        pass

    def construct_map(loader, node):
        data = Map()
        data.line = node.start_mark.line + 1
        yield data
        seen = {}
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge" or not isinstance(
                    key_node, yaml.ScalarNode):
                continue
            key = key_node.value
            if key in seen:
                raise ConstructorError(
                    "while reading a mapping", node.start_mark,
                    f"key {key!r} is given twice (first on line {seen[key]})",
                    key_node.start_mark)
            seen[key] = key_node.start_mark.line + 1
        data.update(loader.construct_mapping(node))

    def construct_date(loader, node):
        try:
            return yaml.SafeLoader.construct_yaml_timestamp(loader, node)
        except ValueError as err:
            raise ConstructorError(None, None,
                                   f"invalid date {node.value!r}: {err}",
                                   node.start_mark) from None

    Loader.add_constructor("tag:yaml.org,2002:map", construct_map)
    Loader.add_constructor("tag:yaml.org,2002:timestamp", construct_date)
    return Loader


def load_yaml(path):
    """Build a gantt from a ``.yml`` file.

    Parameters
    ----------
    path : str or path-like
        File with a ``gantt`` section and a ``tasks`` list.

    Returns
    -------
    Gantt

    Raises
    ------
    GanttError
        Listing every problem found, with its line in the file.
    yaml.YAMLError
        If the file is not valid YAML.
    OSError
        If the file cannot be read.
    """
    import yaml

    with open(path, encoding="utf-8") as f:
        data = yaml.load(f, Loader=_loader())
    if data is None:
        raise GanttError("the file is empty: it needs a 'gantt' section and "
                         "a 'tasks' list")
    return from_dict(data)
